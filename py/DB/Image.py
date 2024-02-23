# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import Optional, Any

from DB.helpers import Session
from DB.helpers.DDL import Index, Column, ForeignKey, Sequence
from DB.helpers.Direct import text
from DB.helpers.Postgres import CHAR, BIGINT, VARCHAR, BYTEA, SMALLINT
from .helpers import Result
from .helpers.ORM import Model
from .helpers.VirtualColumn import VirtualColumnSet, VirtualColumn

MIN_IMGID = 1000  # In prod' it's 1721, this will be used during tests and all-in-one standalone install


class Image(Model):
    __tablename__ = "images"
    imgid = Column(BIGINT, Sequence("seq_images", start=MIN_IMGID))
    # The Object that this image belongs to, with its rank inside
    objid = Column(BIGINT, ForeignKey("obj_head.objid"), primary_key=True)
    imgrank = Column(SMALLINT, primary_key=True)
    width = Column(SMALLINT, nullable=False)
    height = Column(SMALLINT, nullable=False)
    # file_name = Column(VARCHAR(255), nullable=False) # Now computed
    orig_file_name = Column(VARCHAR(255), nullable=False)

    # thumb_file_name = Column(VARCHAR(255)) # Now computed
    thumb_width = Column(SMALLINT)
    thumb_height = Column(SMALLINT)

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

    def img_to_file(self):
        """Return the path in vault to the image"""
        return self.img_from_id_and_orig(self.imgid, self.orig_file_name)

    @staticmethod
    def img_from_id_and_orig(imgid: int, orig_file_name: str) -> str:
        # Images are stored in folders of 10K images max, with original one extension
        ext = orig_file_name[-4:]
        if ext == "jpeg":
            ext = orig_file_name[-5:]
        return "%04d/%04d%s" % (imgid // 10000, imgid % 10000, ext)

    def img_to_thumb_file(self):
        """Return the path in vault to the reduced image, if exists"""
        return self.thumb_img_from_id_if_there(self.imgid, self.thumb_height)

    @staticmethod
    def thumb_img_from_id_if_there(
        imgid: int, thumb_height: Optional[int]
    ) -> Optional[str]:
        # Thumbnails are all .jpg with same naming scheme, if present
        if thumb_height is None:
            return None
        return "%04d/%04d_mini.jpg" % (imgid // 10000, imgid % 10000)

    def __lt__(self, other):
        return self.imgid < other.imgid


class FileNameVirtualColumn(VirtualColumn):
    name = "file_name"
    filler = Image.img_to_file
    sql = "(img.imgid,img.orig_file_name)"  # alt: # return "img_to_file(img.*)"

    @staticmethod
    def result_to_py(from_sel: Any) -> Any:
        # For some SQLAlchemy reason we select a tuple (row) but we get a str
        imgid, orig_file_name = from_sel[1:-1].split(",")
        imgid = int(imgid)
        return Image.img_from_id_and_orig(imgid, orig_file_name)


class ThumbFileNameVirtualColumn(VirtualColumn):
    name = "thumb_file_name"
    filler = Image.img_to_thumb_file
    sql = "(img.thumb_height,img.imgid)"  # alt: "img_to_thumb_file(img.*)"

    @staticmethod
    def result_to_py(from_sel: Any) -> Any:
        # For some SQLAlchemy reason we select a tuple (row) but we get a str
        if from_sel[1] == ",":
            return None  # No height, 99% of the cases
        thumb_height, imgid = [int(n) for n in from_sel[1:-1].split(",")]
        return Image.thumb_img_from_id_if_there(imgid, thumb_height)


IMAGE_VIRTUAL_COLUMNS: VirtualColumnSet = VirtualColumnSet(
    FileNameVirtualColumn, ThumbFileNameVirtualColumn
)


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
    # Same PK as Image, but we can keep here deleted objects reference
    imgid = Column(BIGINT, primary_key=True)
    # Extension shortened
    ext: str = Column(CHAR(3), default="?", server_default="?", nullable=False)
    # State w/r to the application
    state: str = Column(CHAR, default="?", server_default="?", nullable=False)
    # What can be found in digest column
    digest_type: str = Column(CHAR, default="?", server_default="?", nullable=False)
    # A digital signature
    digest = Column(BYTEA, nullable=True)


Index(
    "is_phy_image_file", ImageFile.__table__.c.digest_type, ImageFile.__table__.c.digest
)
