# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import shutil
from os.path import join
from pathlib import Path
from typing import List, Tuple

from API_models.subset import SubsetReq, SubsetRsp, LimitMethods
from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from BO.ObjectSet import DescribedObjectSet, EnumeratedObjectSet, ObjectIDListT
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
from BO.TSVFile import TSVFile
from BO.helpers.ImportHelpers import ImportHow
from DB import Image, ObjectHeader, ObjectFields, Sample, Acquisition, Process, Project
from DB.Object import ObjectCNNFeature
from DB.helpers.Bean import bean_of
from DB.helpers.DBWriter import DBWriter
from DB.helpers.ORM import Query, any_, ResultProxy
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger
from .helpers.TaskService import TaskServiceOnProjectBase

logger = get_logger(__name__)

# Useful typings
# TODO: Put somewhere else if reused in other classes
DBObjectTupleT = Tuple[ObjectHeader, ObjectFields, ObjectCNNFeature, Image, Sample, Acquisition, Process]
DBObjectTupleListT = List[DBObjectTupleT]


class SubsetServiceOnProject(TaskServiceOnProjectBase):
    """
        A task doing the subset operation.
    """
    # Fetch this number of objects at a time, and write them, in a DB session
    CHUNK_SIZE = 100

    def __init__(self, prj_id: int, req: SubsetReq):

        super().__init__(prj_id, req.task_id)
        # Load the destination project
        dest_prj = self.session.query(Project).get(req.dest_prj_id)
        assert dest_prj is not None
        self.dest_prj: Project = dest_prj
        self.req = req
        # Work vars
        self.to_clone: EnumeratedObjectSet = EnumeratedObjectSet(self.session, [])
        self.vault = Vault(join(self.link_src, 'vault'))
        self.first_query = True

    def run(self, current_user_id: int) -> SubsetRsp:
        # Security checks
        RightsBO.user_wants(self.session, current_user_id, Action.READ, self.prj_id)
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, self.dest_prj.projid)
        # OK
        logger.info("Starting subset of '%s'", self.prj.title)
        ret = SubsetRsp()

        self.update_progress(5, "Determining objects to clone")
        self._find_what_to_clone()

        logger.info("Matched %s objects", len(self.to_clone))
        if len(self.to_clone) == 0:
            self.task.taskstate = "Error"
            self.update_progress(10, "No object to include in the subset project")
            ret.errors.append("No object found to clone into subset.")
            return ret

        self._do_clone()
        self.session.commit()

        # Recompute stats and so on
        ProjectBO.do_after_load(self.session, self.dest_prj.projid)
        self.session.commit()
        return ret

    def _do_clone(self):
        """
            Cloning operation itself. Assumes that @see self.to_clone was populated before.
        """
        # Get the mappings in source project, in order to determines the useful columns
        custom_mapping = ProjectMapping().load_from_project(self.prj)
        obj_mapping = custom_mapping.object_mappings
        used_columns = set(obj_mapping.real_cols_to_tsv.keys())
        used_columns.add("orig_id")  # By safety
        # Create a DB writer
        writer = DBWriter(self.session)
        # Narrow the writes in ObjectFields thanks to mappings of original project
        writer.generators({"obj_field": used_columns})
        # Use import helpers
        dest_prj_id = self.dest_prj.projid
        import_how = ImportHow(prj_id=dest_prj_id, update_mode="No",
                               custom_mapping=ProjectMapping(),
                               skip_object_duplicates=False, loaded_files=[])
        # Get parent (enclosing) Sample, Acquisition, Process. There should be 0 in this context...
        import_how.existing_parents = InBundle.fetch_existing_parents(self.session, prj_id=dest_prj_id)

        self._clone_all(import_how, writer)
        # Copy mappings to destination. We could narrow them to the minimum?
        custom_mapping.write_to_project(self.dest_prj)

    def _db_fetch(self, object_ids: ObjectIDListT) -> List[DBObjectTupleT]:
        """
            Do a DB read of given objects, with auxiliary objects.
            :param object_ids: The list of IDs
            :return:
        """
        # TODO: Depending on filter, the joins could be plain (not outer)
        # E.g. if asked for a set of samples
        ret: Query = self.session.query(ObjectHeader, ObjectFields, ObjectCNNFeature, Image, Sample, Acquisition,
                                        Process)
        ret = ret.outerjoin(Image, ObjectHeader.all_images).outerjoin(ObjectCNNFeature).join(ObjectFields)
        ret = ret.join(Sample).join(Acquisition).join(Process, Process.processid == ObjectHeader.acquisid)
        ret = ret.filter(ObjectHeader.objid == any_(object_ids))
        ret = ret.order_by(ObjectHeader.objid)

        if self.first_query:
            logger.info("Query: %s", str(ret))
            self.first_query = False

        return ret.all()

    def _clone_all(self, import_how, writer):

        # Bean counting init
        nb_objects = 0
        total_objects = len(self.to_clone)
        # Pick chunks of object ids
        for a_chunk in self.to_clone.get_objectid_chunks(self.CHUNK_SIZE):
            # Fetch them using SQLAlchemy
            db_tuples = self._db_fetch(a_chunk)
            # Send each 'line'
            for a_db_tuple in db_tuples:
                self._send_to_writer(import_how, writer, a_db_tuple)
                # Bean counting and reporting
                nb_objects += 1
            # Save
            writer.do_bulk_save()
            # Commit (it expires SQLAlchemy session-linked objects)
            self.session.commit()
            progress = int(90 * nb_objects / total_objects)
            self.update_progress(10 + progress, "Subset creation in progress")

    def _send_to_writer(self, import_how: ImportHow, writer: DBWriter, db_tuple: DBObjectTupleT):
        """
            Send a single tuple from DB to DB
        :param import_how:
        :param writer:
        :param db_tuple:
        :return:
        """
        obj_orm, fields_orm, cnn_features_orm, image_orm, sample_orm, acquisition_orm, process_orm = db_tuple
        # Transform all to key-less beans so they can be absorbed by DBWriter
        obj, fields, cnn_features, image, sample, acquisition, process = \
            bean_of(obj_orm), bean_of(fields_orm), bean_of(cnn_features_orm), \
            bean_of(image_orm), bean_of(sample_orm), \
            bean_of(acquisition_orm), bean_of(process_orm)
        assert obj is not None and fields is not None
        # A few fields need adjustment
        obj.img0id = None
        # Cut images if asked so
        if not self.req.do_images:
            image = None
        # Write parent entities
        assert sample and acquisition and process
        dict_of_parents = {Sample.__tablename__: sample,
                           Acquisition.__tablename__: acquisition,
                           Process.__tablename__: process}
        TSVFile.add_parent_objects(import_how, self.session, obj, dict_of_parents)
        # Write object and children
        new_records = TSVFile.create_or_link_slaves(how=import_how,
                                                    session=self.session,
                                                    object_head_to_write=obj,
                                                    object_fields_to_write=fields,
                                                    image_to_write=image)
        writer.add_db_entities(obj, fields, image, new_records)
        # Keep track of existing objects
        if new_records > 1:
            # We now have an Id from sequences, so ref. it.
            import_how.existing_objects[fields.orig_id] = obj.objid
            if cnn_features is not None:
                writer.add_cnn_features(obj, cnn_features)
        # Do images
        if new_records > 0 and self.req.do_images and image and image.file_name is not None:
            # We have an image, with a new imgid but old paths have been copied
            old_imgpath = Path(self.vault.path_to(image.file_name))
            image.file_name = None  # In case, don't reference a non-existing file
            try:
                sub_path = self.vault.store_image(old_imgpath, image.imgid)
                image.file_name = sub_path
            except FileNotFoundError:
                pass
            # Proceed to thumbnail if any
            if image.thumb_file_name is not None:
                old_thumbnail_path = self.vault.path_to(image.thumb_file_name)
                thumb_relative_path, thumb_full_path = self.vault.thumbnail_paths(image.imgid)
                image.thumb_file_name = None  # In case, don't reference a non-existing file
                try:
                    # TODO: Call a primitive in Vault instead
                    shutil.copyfile(old_thumbnail_path, thumb_full_path)
                    image.thumb_file_name = thumb_relative_path
                except FileNotFoundError:
                    pass

    def _find_what_to_clone(self):
        """
            Determine the objects to clone.
        """
        req = self.req
        # From required subsetting method...
        if req.limit_type == LimitMethods.constant:
            rank_function = 'rank'
        elif req.limit_type == LimitMethods.percent:
            rank_function = '100*percent_rank'
        else:
            rank_function = 'FunctionError'

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.session, self.prj_id, self.req.filters)
        selected_tables, where, params = object_set.get_sql(self.task.owner_id)

        sql = """
            SELECT objid FROM (
                SELECT """ + rank_function + """() OVER (PARTITION BY classif_id ORDER BY RANDOM()) rang,
                       obh.objid
                  FROM """ + selected_tables + """
                """ + where.get_sql() + """ ) sr
            WHERE rang <= :ranklimit """
        params['ranklimit'] = self.req.limit_value

        logger.info("SQL=%s", sql)
        logger.info("SQLParam=%s", params)

        res: ResultProxy = self.session.execute(sql, params)
        ids = [r[0] for r in res]
        logger.info("There are %d IDs", len(ids))

        self.to_clone = EnumeratedObjectSet(self.session, ids)
