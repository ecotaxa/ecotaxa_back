# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
from typing import Dict

from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship

from db import Model
from db.Image import Image
from db.Model import minimal_table_of
from db.Object import Object, ObjectFields
from db.Utils import SequenceCache, Bean


# TODO: Dropped in pgAdmin
# self.session.execute("ALTER TABLE obj_field ADD CONSTRAINT obj_field_objfid_fkey DEFERRABLE;")
# self.session.execute("SET CONSTRAINTS obj_field_objfid_fkey DEFERRED;")


class DBWriter(object):
    """
    Database writer (with optimizations).
    """

    def __init__(self, session: Session):
        self.session = session

        self.bulks = []

        self.obj_bulks = []
        self.obj_tbl = None
        self.obj_fields_bulks = []
        self.obj_fields_tbl = None
        self.img_bulks = []
        self.img_tbl = None

        # Save a bit of time for commit
        self.session.execute("SET synchronous_commit TO OFF;")
        self.obj_seq_cache = SequenceCache(self.session, "seq_objects", 100)
        self.img_seq_cache = SequenceCache(self.session, "seq_images", 100)

    do_bulk = False
    use_temp = False
    use_orm_views = False
    use_sqlalchemy_core = True

    def generators(self, target_fields: Dict[str, set]):
        # Small optimization, the below allows minimal SQLAlchemy SQL sent to DB
        metadata = MetaData()
        if self.use_sqlalchemy_core:
            ObjectView = Bean
            self.obj_tbl = minimal_table_of(metadata, Object, target_fields["obj_head"])
            ObjectFieldsView = Bean
            self.obj_fields_tbl = minimal_table_of(metadata, ObjectFields, target_fields["obj_field"])
            ImageView = Bean
            # noinspection PyUnresolvedReferences
            self.img_tbl = Image.__table__
        elif self.use_temp:
            from sqlalchemy.dialects.postgresql import VARCHAR
            ObjectView = Model.partial_clone_of(metadata, Object, target_fields["obj_head"],
                                                [("orig_id", VARCHAR(255))])
            ObjectFieldsView = Model.partial_clone_of(metadata, ObjectFields, target_fields["obj_field"],
                                                      ["orig_id"])
            ImageView = Model.partial_clone_of(metadata, Image, target_fields["image"],
                                               [("orig_id", VARCHAR(255)), "imgrank"])
            ObjectView.__table__.create(self.session.connection())
            ObjectFieldsView.__table__.create(self.session.connection())
            ImageView.__table__.create(self.session.connection())
        elif self.use_orm_views:
            ObjectView = Model.view_of(metadata, Object, target_fields["obj_head"])
            ObjectFieldsView = Model.view_of(metadata, ObjectFields, target_fields["obj_field"])
            ImageView = Model.view_of(metadata, Image, target_fields["image"])
        else:
            ObjectView = Object
            ObjectFieldsView = ObjectFields
            ImageView = Image
        if self.use_orm_views:
            ObjectFieldsView.objhrel = relationship(ObjectView, uselist=False, back_populates="objfrel")
            ObjectView.objfrel = relationship(ObjectFieldsView, uselist=False, back_populates="objhrel")

        return ObjectView, ObjectFieldsView, ImageView

    def do_bulk_save(self):
        if self.do_bulk:
            if not self.bulks:
                return
            nb_bulks = str(len(self.bulks))
            self.session.bulk_save_objects(self.bulks)
            self.bulks.clear()
        elif self.use_sqlalchemy_core:
            nb_bulks = "%d/%d/%d" % (len(self.obj_bulks), len(self.obj_fields_bulks), len(self.img_bulks))
            # TODO: Can be reused?
            inserts = [self.obj_tbl.insert(), self.obj_fields_tbl.insert(), self.img_tbl.insert()]
            # TODO: compiled_cache?
            bulk_sets = [self.obj_bulks, self.obj_fields_bulks, self.img_bulks]
            for a_bulk_set, an_insert in zip(bulk_sets, inserts):
                if not a_bulk_set:
                    continue
                self.session.execute(an_insert, a_bulk_set)
                a_bulk_set.clear()
        logging.info("Batch save objects of %s", nb_bulks)

    def add(self, object_head_to_write, object_fields_to_write, image_to_write, must_write_obj):
        assert object_head_to_write.projid is not None
        assert object_fields_to_write.orig_id is not None
        if self.use_sqlalchemy_core or self.do_bulk:
            # Bulk mode or Core do not create links (using ORM relationship), so we have to do manually
            # Default value from sequences
            if must_write_obj:
                object_head_to_write.objid = self.obj_seq_cache.next()
                object_fields_to_write.objfid = object_head_to_write.objid
            image_to_write.imgid = self.img_seq_cache.next()
            image_to_write.objid = object_head_to_write.objid
        if self.use_sqlalchemy_core:
            if must_write_obj:
                self.obj_fields_bulks.append(object_fields_to_write)
                self.obj_bulks.append(object_head_to_write)
            self.img_bulks.append(image_to_write)
        elif self.do_bulk:
            self.bulks.append(object_fields_to_write)
            self.bulks.append(object_head_to_write)
        else:
            self.session.add(object_head_to_write)
            self.session.add(object_fields_to_write)

    def close_row(self):
        if self.do_bulk or self.use_sqlalchemy_core:
            # The UPDATE should take place in the batch
            # self.bulks.append(image_to_write)
            pass
        else:
            self.session.flush()

    def persist(self):
        if self.do_bulk or self.use_sqlalchemy_core:
            self.do_bulk_save()
        else:
            self.session.commit()

    def eof_cleanup(self):

        if self.use_temp:
            ObjectFieldsGen.__table__.drop(self.session.connection())
            ObjectGen.__table__.drop(self.session.connection())
            ImageGen.__table__.drop(self.session.connection())

        self.session.commit()

    def link(self, object_fields_to_write, object_head_to_write):
        # Add, using ORM, the ObjectFields twin
        if not (self.bulks or self.use_sqlalchemy_core):
            object_fields_to_write.objhrel = object_head_to_write
