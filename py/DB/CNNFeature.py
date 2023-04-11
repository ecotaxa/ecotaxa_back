# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

from .Object import ObjectIDT
from .helpers.Bean import Bean
from .helpers.DDL import ForeignKey
from .helpers.ORM import Column, relationship, Model
from .helpers.Postgres import BIGINT, REAL


class ObjectCNNFeature(Model):
    __tablename__ = "obj_cnn_features"
    objcnnid: int = Column(
        BIGINT, ForeignKey("obj_head.objid", ondelete="CASCADE"), primary_key=True
    )
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship


# The features in _each_ row
DEEP_FEATURES = ["cnn%02d" % i for i in range(1, 51)]

for a_feat in DEEP_FEATURES:
    setattr(ObjectCNNFeature, a_feat, Column(REAL))


class ObjectCNNFeaturesBean(Bean):
    """
    A bean for feeding DBWriter.
    """

    def __init__(self, obj_id: ObjectIDT, features: List[float]):
        super().__init__(zip(DEEP_FEATURES, features))
        self["objcnnid"] = obj_id
