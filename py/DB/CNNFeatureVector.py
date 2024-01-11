# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List
from pgvector.sqlalchemy import Vector

from .Object import ObjectIDT
from .helpers.Bean import Bean
from .helpers.DDL import ForeignKey
from .helpers.ORM import Column, relationship, Model
from .helpers.Postgres import BIGINT, REAL

N_DEEP_FEATURES = 50


class ObjectCNNFeatureVector(Model):
    __tablename__ = "obj_cnn_features_vector"
    objcnnid: int = Column(
        BIGINT, ForeignKey("obj_head.objid", ondelete="CASCADE"), primary_key=True
    )
    features: Vector = Column(Vector(N_DEEP_FEATURES))
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship


class ObjectCNNFeaturesVectorBean(Bean):
    """
    A bean for feeding DBWriter.
    """

    def __init__(self, obj_id: ObjectIDT, features: List[float]):
        super().__init__({
            "objcnnid": obj_id,
            "features": features,
        })
