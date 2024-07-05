# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum

from DB.helpers import Session
from DB.helpers.DDL import Index, Column, ForeignKey, Sequence
from DB.helpers.Direct import text
from DB.helpers.Postgres import CHAR, BIGINT, VARCHAR, INTEGER, BYTEA
from .helpers import Result
from .helpers.ORM import Model


class Image(Model):
    __tablename__ = "images"
    # TODO: The PK is unused from DB stats, we only use the "real PK" below
    imgid = Column(BIGINT, Sequence("seq_images"), primary_key=True)
    # The Object that this image belongs to
    # TODO: It looks like we have a relationship cycle Object->Image->Object
    #  Probably due to the fact that several images can exist for a single Object
    # Real PK: objid + imgrank unless we can share images b/w objects... WIP
    # TODO: objid is nullable=False
    objid = Column(BIGINT, ForeignKey("obj_head.objid"))
    imgrank = Column(INTEGER, nullable=False)
    file_name = Column(VARCHAR(255), nullable=False)
    orig_file_name = Column(VARCHAR(255), nullable=False)
    width = Column(INTEGER, nullable=False)
    height = Column(INTEGER, nullable=False)

    thumb_file_name = Column(VARCHAR(255))
    thumb_width = Column(INTEGER)
    thumb_height = Column(INTEGER)

    @staticmethod
    def fetch_existing_images(session: Session, prj_id):
        """
        Get all object/image pairs from the project
        """
        # Must be reloaded from DB, as phase 1 added all objects for duplicates checking
        # TODO: Why using the view?
        sql = text(
            "SELECT concat(o.orig_id,'*',i.orig_file_name) "
            "  FROM images i "
            "  JOIN objects o ON i.objid = o.objid "
            " WHERE o.projid = :prj"
        )
        res: Result = session.execute(sql, {"prj": prj_id})
        ret = {img_id for img_id, in res}
        return ret

    def __lt__(self, other):
        return self.imgid < other.imgid


# Covering and unicity-enforcing index with rank
Index(
    "is_imageobjrank", Image.__table__.c.objid, Image.__table__.c.imgrank, unique=True
)
# To track corresponding files
Index("is_image_file", Image.__table__.c.file_name)


class ImageFileStateEnum(Enum):
    # Not known
    UNKNOWN = "?"
    # OK computed
    OK = "O"
    # Image referenced from DB but not in FS
    MISSING = "M"
    # There was an unexpected error trying to assert this image status
    ERROR = "E"


class ImageFile(Model):
    # An image on disk. Can be referenced (or not...) from the application
    __tablename__ = "image_file"
    # Path inside the Vault
    path: str = Column(VARCHAR, primary_key=True)
    # State w/r to the application
    state: str = Column(CHAR, default="?", server_default="?", nullable=False)
    # What can be found in digest column
    digest_type: str = Column(CHAR, default="?", server_default="?", nullable=False)
    # A digital signature
    digest = Column(BYTEA, nullable=True)


Index(
    "is_phy_image_file", ImageFile.__table__.c.digest_type, ImageFile.__table__.c.digest
)
