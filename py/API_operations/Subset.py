# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Set, Iterable

from API_models.subset import SubsetReq, SubsetRsp, LimitMethods, GroupDefinitions
from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from BO.ObjectSet import DescribedObjectSet, EnumeratedObjectSet, ObjectIDListT
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
from BO.TSVFile import TSVFile
from BO.helpers.ImportHelpers import ImportHow
from DB.Acquisition import Acquisition
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from DB.Image import Image
from DB.Object import ObjectHeader, ObjectFields, ObjectsClassifHisto
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample
from DB.helpers import Result
from DB.helpers.Bean import bean_of, Bean
from DB.helpers.DBWriter import DBWriter
from DB.helpers.Direct import text
from DB.helpers.ORM import any_
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger, LogsSwitcher
from .helpers.JobService import JobServiceOnProjectBase, ArgsDict

logger = get_logger(__name__)

# Useful typings
# TODO: Put somewhere else if reused in other classes
DBObjectTupleT = Tuple[
    ObjectHeader, ObjectFields, ObjectCNNFeatureVector, Image, Sample, Acquisition, Process
]
DBObjectTupleListT = List[DBObjectTupleT]


class SubsetServiceOnProject(JobServiceOnProjectBase):
    """
    A task doing the subset operation.
    """

    JOB_TYPE = "Subset"

    # Fetch this number of objects at a time, and write them, in a DB session
    CHUNK_SIZE = 100

    def __init__(self, prj_id: int, req: SubsetReq):
        super().__init__(prj_id)
        # Load the destination project
        dest_prj = self.get_session().query(Project).get(req.dest_prj_id)
        assert dest_prj is not None
        self.dest_prj: Project = dest_prj
        self.req = req
        # Work vars
        self.to_clone: EnumeratedObjectSet = EnumeratedObjectSet(self.get_session(), [])
        self.vault = Vault(self.config.vault_dir())
        self.first_query = True
        self.images_per_orig_id: Dict[str, Set[int]] = {}

    def init_args(self, args: ArgsDict) -> ArgsDict:
        super().init_args(args)
        args["req"] = self.req.dict()
        return args

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        json_args["req"] = SubsetReq(**json_args["req"])

    def run(self, current_user_id: int) -> SubsetRsp:
        """
        Initial run, basically just create the job.
        """
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.READ, self.prj_id)
        RightsBO.user_wants(
            self.session, current_user_id, Action.ADMINISTRATE, self.dest_prj.projid
        )
        # Security OK, create pending job
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = SubsetRsp(job_id=self.job_id)
        return ret

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            return self.do_run()

    def do_run(self) -> None:
        # OK
        logger.info("Starting subset of '%s'", self.prj.title)

        self.update_progress(5, "Determining objects to clone")
        self._find_what_to_clone()

        logger.info("Matched %s objects", len(self.to_clone))
        if len(self.to_clone) == 0:
            errors = ["No object found to clone into subset."]
            self.set_job_result(errors=errors, infos={"infos": ""})
            return

        self._do_clone()
        self.session.commit()

        # Recompute stats and so on
        ProjectBO.do_after_load(self.session, self.dest_prj.projid)
        self.session.commit()

        self.set_job_result(errors=[], infos={"rowcount": len(self.to_clone)})

    def _do_clone(self) -> None:
        """
        Cloning operation itself. Assumes that @see self.to_clone was populated before.
        """
        # Get the mappings in source project, in order to determine the useful columns
        custom_mapping = ProjectMapping().load_from_project(self.prj)
        obj_mapping = custom_mapping.object_mappings
        used_columns = set(obj_mapping.real_cols_to_tsv.keys())
        used_columns.add("orig_id")  # By safety
        # Create a DB writer
        writer = DBWriter(self.session)
        # Narrow the writes in ObjectFields thanks to mappings of original project
        writer.generators({ObjectFields.__tablename__: used_columns})
        # Use import helpers
        dest_prj_id = self.dest_prj.projid
        import_how = ImportHow(
            prj_id=dest_prj_id,
            update_mode="No",
            custom_mapping=ProjectMapping(),
            skip_object_duplicates=False,
            loaded_files=[],
        )
        # Get parent (enclosing) Sample, Acquisition. There should be 0 in this context as the project is new.
        (
            import_how.existing_samples,
            import_how.existing_acquisitions,
        ) = InBundle.fetch_existing_parents(self.session, prj_id=dest_prj_id)

        self._clone_all(import_how, writer)
        # Copy mappings to destination. We could narrow them to the minimum?
        custom_mapping.write_to_project(self.dest_prj)

    def _db_fetch(self, object_ids: ObjectIDListT) -> Iterable[DBObjectTupleT]:
        """
        Do a DB read of given objects, with auxiliary objects.
        :param object_ids: The list of IDs
        :return:
        """
        # TODO: Depending on filter, the joins could be plain (not outer)
        # E.g. if asked for a set of samples
        ret = self.ro_session.query(ObjectHeader)
        ret = (
            ret.join(ObjectHeader.acquisition)
            .join(Acquisition.process)
            .join(Acquisition.sample)
        )
        ret = (
            ret.outerjoin(Image, ObjectHeader.all_images)
            .outerjoin(ObjectCNNFeatureVector)
            .join(ObjectFields)
        )
        ret = ret.filter(ObjectHeader.objid == any_(object_ids))
        ret = ret.order_by(ObjectHeader.objid, Image.imgid)
        ret = ret.with_entities(
            ObjectHeader,
            ObjectFields,
            ObjectCNNFeatureVector,
            Image,
            Sample,
            Acquisition,
            Process,
        )

        if self.first_query:
            logger.info("Query: %s", str(ret))
            self.first_query = False

        return ret

    def _db_fetch_histo(
        self, object_ids: ObjectIDListT
    ) -> Iterable[ObjectsClassifHisto]:
        """
        Do a DB read of classification history.
        """
        ret = self.ro_session.query(ObjectsClassifHisto)
        ret = ret.filter(ObjectsClassifHisto.objid == any_(object_ids))
        return ret

    def _clone_all(self, import_how: ImportHow, writer: DBWriter) -> None:
        # Bean counting init
        nb_objects = 0
        total_objects = len(self.to_clone)
        # Pick chunks of object ids
        for a_chunk in self.to_clone.get_objectid_chunks(self.CHUNK_SIZE):
            # Fetch them using SQLAlchemy
            db_tuples = self._db_fetch(a_chunk)
            db_histo = self._db_fetch_histo(a_chunk)
            # Rationalize histo as there is lots of rows
            db_histo_dict: Dict[int, List[ObjectsClassifHisto]] = {}
            for an_histo in db_histo:
                assert an_histo.objid is not None
                db_histo_dict.setdefault(an_histo.objid, list()).append(an_histo)
            # Send each 'line'
            for a_db_tuple in db_tuples:
                self._send_to_writer(import_how, writer, a_db_tuple, db_histo_dict)
            # Bean counting and reporting
            nb_objects += len(a_chunk)
            # Save
            writer.do_bulk_save()
            # Commit (it expires SQLAlchemy session-linked objects)
            self.session.commit()
            progress = int(90 * nb_objects / total_objects)
            self.update_progress(10 + progress, "Subset creation in progress")

    def _send_to_writer(
        self,
        import_how: ImportHow,
        writer: DBWriter,
        db_tuple: DBObjectTupleT,
        db_histo: Dict[int, List[ObjectsClassifHisto]],
    ) -> None:
        """
            Send a set of tuples from DB to DB
        :param import_how:
        :param writer:
        :param db_tuple:
        :return:
        """
        (
            obj_orm,
            fields_orm,
            cnn_features_orm,
            image_orm,
            sample_orm,
            acquisition_orm,
            process_orm,
        ) = db_tuple
        assert obj_orm.objid  # mypy
        histo_for_obj = db_histo.get(obj_orm.objid, [])
        histo: List[Bean] = []
        for a_histo in histo_for_obj:
            bean = bean_of(a_histo)
            assert bean  # mypy
            bean.classif_date = a_histo.classif_date  # Reconstitute PK
            bean.classif_who = a_histo.classif_who  # Another erased key
            histo.append(bean)
        # Transform all to key-less beans so they can be absorbed by DBWriter
        obj, fields, cnn_features, image, sample, acquisition, process = (
            bean_of(obj_orm),
            bean_of(fields_orm),
            bean_of(cnn_features_orm),
            bean_of(image_orm),
            bean_of(sample_orm),
            bean_of(acquisition_orm),
            bean_of(process_orm),
        )
        # Minimum is object + fields
        assert obj is not None and fields is not None
        # Write parent entities
        assert sample and acquisition and process
        dict_of_parents = {
            Sample.__tablename__: sample,
            Acquisition.__tablename__: acquisition,
            Process.__tablename__: process,
        }
        TSVFile.add_parent_objects(import_how, self.session, obj, dict_of_parents)
        # Propagate last human operator on the object
        obj.classif_who = obj_orm.classif_who
        # Write object and children
        new_records = TSVFile.create_or_link_slaves(
            how=import_how,
            session=self.session,
            object_head_to_write=obj,
            object_fields_to_write=fields,
            image_to_write=image,
        )
        writer.add_db_entities(obj, fields, image, new_records)
        # Keep track of existing objects
        if new_records > 1:  # TODO: This is a cumbersome way of stating "new object",
            # as an object is obj_head + obj_fields i.e. 2 records
            self.images_per_orig_id[obj.orig_id] = set()
            # We now have an Id from sequences, so ref. it.
            # this is needed for proper detection of subsequent images when there are 1+
            import_how.existing_objects[obj.orig_id] = obj.objid
            if cnn_features is not None:
                writer.add_cnn_features(obj, cnn_features)
            writer.add_classif_log(obj, histo)
        # Do images
        if new_records > 0 and image and image.file_name is not None:
            # We have an image, with a new imgid but old paths have been copied
            old_imgpath = Path(self.vault.image_path(image.file_name))
            image.file_name = None  # In case, don't reference a non-existing file
            try:
                sub_path = self.vault.store_image(old_imgpath, image.imgid)
                image.file_name = sub_path
            except FileNotFoundError:
                logger.error("Could not duplicate %s, not found", old_imgpath)
            # Proceed to thumbnail if any
            if image.thumb_file_name is not None:
                old_thumbnail_path = self.vault.image_path(image.thumb_file_name)
                thumb_relative_path, thumb_full_path = self.vault.thumbnail_paths(
                    image.imgid
                )
                image.thumb_file_name = (
                    None  # In case, don't reference a non-existing file
                )
                try:
                    # TODO: Call a primitive in Vault instead
                    shutil.copyfile(old_thumbnail_path, thumb_full_path)
                    image.thumb_file_name = thumb_relative_path
                except FileNotFoundError:
                    logger.error(
                        "Could not duplicate thumbnail %s, not found", old_imgpath
                    )
            # Some imgrank are rotten, and the DB does not enforce unicity per object
            images_for_obj = self.images_per_orig_id[obj.orig_id]
            if image.imgrank in images_for_obj:
                image.imgrank = max(images_for_obj) + 1
            images_for_obj.add(image.imgrank)

    def _find_what_to_clone(self) -> None:
        """
        Determine the objects to clone.
        """
        req = self.req
        # From required subsetting method...
        if req.limit_type == LimitMethods.constant:
            rank_function = "rank"
        elif req.limit_type == LimitMethods.percent:
            rank_function = "100*percent_rank"
        else:
            rank_function = "FunctionError"
        # And repartition key
        if req.group_type == GroupDefinitions.categories:
            part_key = "obh.classif_id"
        elif req.group_type == GroupDefinitions.samples:
            part_key = "sam.sampleid"
        elif req.group_type == GroupDefinitions.acquisitions:
            part_key = "acq.acquisid"
        else:
            part_key = "???"

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.session, self.prj, self._get_owner_id(), self.req.filters
        )
        from_, where, params = object_set.get_sql()

        # noinspection SqlResolve
        sql = (
            """
            SELECT objid FROM (
                SELECT """
            + rank_function
            + """() OVER (PARTITION BY """
            + part_key
            + """ ORDER BY RANDOM()) rang,
                       obh.objid
                  FROM """
            + from_.get_sql()
            + """
                """
            + where.get_sql()
            + """ ) sr
            WHERE rang <= :ranklimit """
        )
        params["ranklimit"] = self.req.limit_value

        logger.info("SQL=%s", sql)
        logger.info("SQLParam=%s", params)

        res: Result = self.ro_session.execute(text(sql), params)
        ids = [r for r, in res]
        logger.info("There are %d IDs", len(ids))

        self.to_clone = EnumeratedObjectSet(self.session, ids)
