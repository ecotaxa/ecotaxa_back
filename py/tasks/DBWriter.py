# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict

# noinspection PyPackageRequirements
from sqlalchemy import MetaData
# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from db.Image import Image
from db.Model import minimal_table_of
from db.Object import Object, ObjectFields
from db.Utils import SequenceCache, Bean
from tech.DynamicLogs import get_logger

logger = get_logger(__name__)


# TODO: Dropped in pgAdmin
# self.session.execute("ALTER TABLE obj_field ADD CONSTRAINT obj_field_objfid_fkey DEFERRABLE;")
# self.session.execute("SET CONSTRAINTS obj_field_objfid_fkey DEFERRED;")


class DBWriter(object):
    """
        Database writer for import (with optimizations).
        @see SQLAlchemy Core documentation for principles.
    """
    SEQUENCE_CACHE_SIZE = 100

    def __init__(self, session: Session):
        self.session = session

        self.obj_bulks = []
        self.obj_tbl = None
        self.obj_fields_bulks = []
        self.obj_fields_tbl = None
        self.img_bulks = []
        self.img_tbl = None

        # Save a bit of time for commit
        self.session.execute("SET synchronous_commit TO OFF;")
        self.obj_seq_cache = SequenceCache(self.session, "seq_objects", self.SEQUENCE_CACHE_SIZE)
        self.img_seq_cache = SequenceCache(self.session, "seq_images", self.SEQUENCE_CACHE_SIZE)

    # The properties used in code, not in mapping. If not listed here they are not persisted
    # TODO: Provoke a crash at runtime for tests if one is forgotten. Dropping data silently is bad.
    obj_head_prog_cols = {'sunpos', 'random_value', 'acquisid', 'processid', 'sampleid'}
    obj_fields_prog_cols = {}

    def generators(self, target_fields: Dict[str, set]):
        # Small optimization, the below allows minimal SQLAlchemy SQL sent to DB
        metadata = MetaData()
        ObjectView = Bean
        obj_head_cols = target_fields["obj_head"].union(self.obj_head_prog_cols)
        self.obj_tbl = minimal_table_of(metadata, Object, obj_head_cols)
        ObjectFieldsView = Bean
        obj_fields_cols = target_fields["obj_field"].union(self.obj_fields_prog_cols)
        self.obj_fields_tbl = minimal_table_of(metadata, ObjectFields, obj_fields_cols)
        ImageView = Bean
        # noinspection PyUnresolvedReferences
        self.img_tbl = Image.__table__

        return ObjectView, ObjectFieldsView, ImageView

    def do_bulk_save(self):
        nb_bulks = "%d/%d/%d" % (len(self.obj_bulks), len(self.obj_fields_bulks), len(self.img_bulks))
        # TODO: Can be reused?
        inserts = [self.obj_tbl.insert(), self.obj_fields_tbl.insert(), self.img_tbl.insert()]
        # TODO: SQLAlchemy compiled_cache?
        bulk_sets = [self.obj_bulks, self.obj_fields_bulks, self.img_bulks]
        for a_bulk_set, an_insert in zip(bulk_sets, inserts):
            if not a_bulk_set:
                continue
            self.session.execute(an_insert, a_bulk_set)
            a_bulk_set.clear()
        logger.info("Batch save objects of %s", nb_bulks)

    def add_db_entities(self, object_head_to_write, object_fields_to_write, image_to_write, must_write_obj):
        # Bulk mode or Core do not create links (using ORM relationship), so we have to do manually
        if must_write_obj:
            assert object_head_to_write.projid is not None
            assert object_fields_to_write.orig_id is not None
            # Default value from sequences
            object_head_to_write.objid = self.obj_seq_cache.next()
            object_fields_to_write.objfid = object_head_to_write.objid
        # There is at least an image
        image_to_write.imgid = self.img_seq_cache.next()
        image_to_write.objid = object_head_to_write.objid
        if must_write_obj:
            self.obj_fields_bulks.append(object_fields_to_write)
            self.obj_bulks.append(object_head_to_write)
        self.img_bulks.append(image_to_write)

    def add_vignette_backup(self, object_head_to_write, backup_img_to_write):
        backup_img_to_write.objid = object_head_to_write.objid
        backup_img_to_write.imgid = self.img_seq_cache.next()
        self.img_bulks.append(backup_img_to_write)

    def persist(self):
        self.do_bulk_save()

    def eof_cleanup(self):
        self.session.commit()


# noinspection PyUnreachableCode
if False:  # pragma: no cover
    class DBWriterPlain(object):
        """
        Database writer (without optimizations).
        """
        # noinspection PyPackageRequirements
        from sqlalchemy.orm import Session

        def __init__(self, session: Session):
            self.session = session

            self.obj_bulks = []
            self.obj_tbl = None
            self.obj_fields_bulks = []
            self.obj_fields_tbl = None
            self.img_bulks = []
            self.img_tbl = None

        @staticmethod
        def generators():
            # Small optimization, the below allows minimal SQLAlchemy SQL sent to DB
            # Plain base objects with relations
            ObjectView = Object
            ObjectFieldsView = ObjectFields
            ImageView = Image

            return ObjectView, ObjectFieldsView, ImageView

        def do_bulk_save(self):
            pass

        def add_db_entities(self, object_head_to_write, object_fields_to_write, _image_to_write, _must_write_obj):
            assert object_head_to_write.projid is not None
            assert object_fields_to_write.orig_id is not None
            self.session.add(object_head_to_write)
            self.session.add(object_fields_to_write)

        def add_vignette_backup(self, _object_head_to_write, backup_img_to_write):
            self.session.add(backup_img_to_write)

        def close_row(self):
            self.session.flush()

        def persist(self):
            self.session.commit()

        def eof_cleanup(self):
            self.session.commit()

        @staticmethod
        def link(object_fields_to_write, object_head_to_write):
            # Add, using ORM, the ObjectFields twin
            object_fields_to_write.objhrel = object_head_to_write
