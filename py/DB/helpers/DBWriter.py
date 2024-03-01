# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Optional, ClassVar

from helpers.DynamicLogs import get_logger
from .Bean import Bean
from .Direct import text
from .ORM import Session, MetaData, minimal_table_of
from .Postgres import SequenceCache
from ..CNNFeature import ObjectCNNFeature
from ..Image import Image
from ..Object import ObjectHeader, ObjectFields, ObjectsClassifHisto

logger = get_logger(__name__)


# TODO: Dropped in pgAdmin
# self.session.execute("ALTER TABLE obj_field ADD CONSTRAINT obj_field_objfid_fkey DEFERRABLE;")
# self.session.execute("SET CONSTRAINTS obj_field_objfid_fkey DEFERRED;")


class DBWriter(object):
    """
    Database writer for import/subset/CNN (with optimizations).
    @see SQLAlchemy Core documentation for principles.
    """

    SEQUENCE_CACHE_SIZE: ClassVar = 100

    def __init__(self, session: Session):
        self.session = session

        self.obj_tbl = ObjectHeader.__table__
        self.obj_fields_tbl = ObjectFields.__table__  # Slow by default @see narrow_to
        self.img_tbl = Image.__table__
        self.obj_cnn_tbl = ObjectCNNFeature.__table__
        self.obj_history_tbl = ObjectsClassifHisto.__table__
        # Data
        self.obj_bulks: List[Bean] = []
        self.obj_fields_bulks: List[Bean] = []
        self.img_bulks: List[Bean] = []
        self.obj_cnn_bulks: List[Bean] = []
        self.obj_history_bulks: List[Bean] = []

        # Save a bit of time for commit
        self.session.execute(text("SET synchronous_commit TO OFF;"))
        self.obj_seq_cache = SequenceCache(
            self.session, "seq_objects", self.SEQUENCE_CACHE_SIZE
        )
        self.img_seq_cache = SequenceCache(
            self.session, "seq_images", self.SEQUENCE_CACHE_SIZE
        )

    obj_fields_prog_cols = {ObjectFields.acquis_id.name}

    def narrow_to(self, target_fields: set):
        # Small optimization, the below allows minimal SQLAlchemy SQL sent to DB for large fields table
        metadata = MetaData()
        obj_fields_cols = target_fields.union(self.obj_fields_prog_cols)
        self.obj_fields_tbl = minimal_table_of(metadata, ObjectFields, obj_fields_cols)

    def do_bulk_save(self) -> None:
        nb_bulks = "%d/%d/%d/%d/%d" % (
            len(self.obj_bulks),
            len(self.obj_fields_bulks),
            len(self.obj_cnn_bulks),
            len(self.img_bulks),
            len(self.obj_history_bulks),
        )
        # TODO: Can be reused?
        inserts = [
            self.obj_tbl.insert(),
            self.obj_fields_tbl.insert(),
            self.obj_cnn_tbl.insert(),
            self.img_tbl.insert(),
            self.obj_history_tbl.insert(),
        ]
        # TODO: SQLAlchemy compiled_cache?
        bulk_sets = [
            self.obj_bulks,
            self.obj_fields_bulks,
            self.obj_cnn_bulks,
            self.img_bulks,
            self.obj_history_bulks,
        ]
        for a_bulk_set, an_insert in zip(bulk_sets, inserts):
            if not a_bulk_set:
                continue
            self.session.execute(an_insert, a_bulk_set)
            a_bulk_set.clear()
        logger.info("Batch save objects of %s", nb_bulks)

    def add_db_entities(
        self,
        object_head_to_write: Bean,
        object_fields_to_write: Bean,
        image_to_write: Optional[Bean],
        new_records: int,
    ) -> None:
        # Bulk mode or Core do not create links (using ORM relationship), so we have to do manually
        if new_records > 1:
            # There is a new image and more
            # assert object_head_to_write.projid is not None
            assert object_head_to_write.orig_id is not None
            # Default value from sequences
            object_head_to_write.objid = self.obj_seq_cache.next()
            object_fields_to_write.objfid = object_head_to_write.objid
            object_fields_to_write.acquis_id = object_head_to_write.acquisid
        if new_records >= 1 and image_to_write:
            # There is (potentially just) a new image
            image_to_write.imgid = self.img_seq_cache.next()
            image_to_write.objid = object_head_to_write.objid
        if new_records > 1:
            # There is a new image and more
            self.obj_fields_bulks.append(object_fields_to_write)
            self.obj_bulks.append(object_head_to_write)
        if new_records >= 1 and image_to_write:
            # There is (potentially just) a new image
            self.img_bulks.append(image_to_write)

    def add_vignette_backup(self, object_head_to_write, backup_img_to_write) -> None:
        backup_img_to_write.objid = object_head_to_write.objid
        backup_img_to_write.imgid = self.img_seq_cache.next()
        self.img_bulks.append(backup_img_to_write)

    def add_cnn_features(self, object_head_to_write, cnn_features: Bean) -> None:
        cnn_features.objcnnid = object_head_to_write.objid
        self.obj_cnn_bulks.append(cnn_features)

    def add_classif_log(self, object_head_to_write, classif_histo: List[Bean]) -> None:
        for a_bean in classif_histo:
            a_bean.objid = object_head_to_write.objid
        self.obj_history_bulks.extend(classif_histo)

    def add_cnn_features_with_pk(self, cnn_features: Bean) -> None:
        self.obj_cnn_bulks.append(cnn_features)

    def persist(self) -> None:
        self.do_bulk_save()

    def eof_cleanup(self) -> None:
        self.session.commit()
