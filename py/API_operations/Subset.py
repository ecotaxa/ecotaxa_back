# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import shutil
from os.path import join
from pathlib import Path
from typing import List, Tuple, Iterator

from API_models.subset import SubsetReq, SubsetRsp, LimitMethods
from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from BO.ObjectSet import ObjectSet
from BO.Project import ProjectBO
from BO.TSVFile import TSVFile
from BO.helpers.ImportHelpers import ImportHow
from DB import Image, Object, ObjectFields, Sample, Acquisition, Process
from DB import Query, any_, ResultProxy
from DB.Object import ObjectCNNFeature
from DB.helpers.Bean import bean_of
from DB.helpers.DBWriter import DBWriter
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger
from .helpers.TaskService import TaskServiceBase

logger = get_logger(__name__)

# Useful typings
DBObjectTupleT = Tuple[Object, ObjectFields, ObjectCNNFeature, Image, Sample, Acquisition, Process]
DBObjectTupleListT = List[DBObjectTupleT]


class SubsetService(TaskServiceBase):
    """
        A task doing the subset operation.
    """
    # Fetch this number of objects at a time, and write them, in a DB session
    CHUNK_SIZE = 100

    def __init__(self, prj_id: int, req: SubsetReq):

        super().__init__(prj_id, req.task_id)
        self.dest_prj_id = req.dest_prj_id
        self.req = req
        self.to_clone: List[int] = []
        self.vault = Vault(join(self.link_src, 'vault'))
        self.first_query = True

    def run(self) -> SubsetRsp:
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

        # Recompute stats and so on
        ProjectBO.do_after_load(self.session, self.dest_prj_id)
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
        dest_prj_id = self.dest_prj_id
        import_how = ImportHow(prj_id=dest_prj_id, update_mode="No",
                               custom_mapping=ProjectMapping(),
                               skip_object_duplicates=False, loaded_files=[])
        # Get parent (enclosing) Sample, Acquisition, Process. There should be 0 in this context...
        import_how.existing_parents = InBundle.fetch_existing_parents(self.session, prj_id=self.dest_prj_id)

        self._clone_all(import_how, writer)

    def _db_fetch(self, objids: List[int]) -> List[DBObjectTupleT]:
        """
            Do a DB read of given objects, with auxiliary objects.
            :param objids:
            :return:
        """
        # TODO: Depending on filter, the joins could be plain (not outer)
        # E.g. if asked for a set of samples
        ret: Query = self.session.query(Object, ObjectFields, ObjectCNNFeature, Image, Sample, Acquisition, Process)
        ret = ret.outerjoin(Image, Object.all_images).outerjoin(ObjectCNNFeature).join(ObjectFields)
        ret = ret.outerjoin(Sample).outerjoin(Acquisition).outerjoin(Process)
        ret = ret.filter(Object.objid == any_(objids))  # type: ignore
        ret = ret.order_by(Object.objid)

        if self.first_query:
            logger.info("Query: %s", str(ret))
            self.first_query = False

        return ret.all()

    def _get_objectid_chunks(self) -> Iterator[List[int]]:
        """
            Yield successive n-sized chunks from l.
            Adapted from
            https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks/312464#312464
        """
        lst = self.to_clone
        siz = self.CHUNK_SIZE
        for idx in range(0, len(lst), siz):
            yield lst[idx:idx + siz]

    def _clone_all(self, import_how, writer):

        # Bean counting init
        nb_objects = 0
        total_objects = len(self.to_clone)
        # Pick chunks of object ids
        for a_chunk in self._get_objectid_chunks():
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

    def _send_to_writer(self, import_how, writer, db_tuple: DBObjectTupleT):
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
        # Write parent entities if needed
        dict_of_parents = {}
        if process:
            dict_of_parents[Process.__tablename__] = process.__dict__
        if sample:
            dict_of_parents[Sample.__tablename__] = sample.__dict__
        if acquisition:
            dict_of_parents[Acquisition.__tablename__] = acquisition.__dict__
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
        object_set: ObjectSet = ObjectSet(self.session, self.prj_id, self.req.filters)
        where, params = object_set.get_sql(self.task.owner_id)

        sql = """
            SELECT objid FROM (
                SELECT """ + rank_function + """() OVER (PARTITION BY classif_id ORDER BY RANDOM()) rang,
                       o.objid
                  FROM objects o
                """ + where.get_sql() + """ ) sr
            WHERE rang <= :ranklimit """
        params['ranklimit'] = self.req.limit_value

        logger.info("SQLParam=%s", params)

        res: ResultProxy = self.session.execute(sql, params)
        ids = [r['objid'] for r in res]
        logger.info("There are %d IDs", len(ids))

        self.to_clone = ids
