# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy import Index, Column, ForeignKey, Sequence
from sqlalchemy.dialects.postgresql import BIGINT, VARCHAR, INTEGER

from db.Model import Model


# TODO: Why the ORM does not generate a DEFAULT?
class Image(Model):
    __tablename__ = 'images'
    imgid = Column(BIGINT, Sequence('seq_images'), primary_key=True)
    # The Object that this image belongs to
    # TODO: It looks like we have a relationship cycle Object->Image->Object
    #  Probably due to the fact that several images can exist for a single Object
    # Real PK: objid + imgrank or better orig_id + imgrank
    objid = Column(BIGINT, ForeignKey('obj_head.objid'))
    imgrank = Column(INTEGER)
    file_name = Column(VARCHAR(255))
    orig_file_name = Column(VARCHAR(255))
    width = Column(INTEGER)
    height = Column(INTEGER)
    thumb_file_name = Column(VARCHAR(255))
    thumb_width = Column(INTEGER)
    thumb_height = Column(INTEGER)


Index('IS_ImagesObjects', Image.objid)
