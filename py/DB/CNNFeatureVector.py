# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2022-2024 LOVNOWER : Amblard, Colin, Irisson, Reutenauer (UPMC-CNRS-FOTONOWER)
#
from typing import List

from pgvector.sqlalchemy import Vector  # type:ignore

from .Object import ObjectIDT
from .helpers.Bean import Bean
from .helpers.DDL import ForeignKey, Index
from .helpers.ORM import Column, relationship, Model
from .helpers.Postgres import BIGINT

N_DEEP_FEATURES = 50


class ObjectCNNFeatureVector(Model):
    __tablename__ = "obj_cnn_features_vector"
    objcnnid: int = Column(
        BIGINT, ForeignKey("obj_head.objid", ondelete="CASCADE"), primary_key=True
    )
    features: Vector = Column(Vector(N_DEEP_FEATURES))
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship


# Note: below is OK for CI but different in PROD, see TODO
Index(
    "obj_cnn_features_vector_hv_ivfflat_l2_5k_idx",
    ObjectCNNFeatureVector.features,
    postgresql_using="ivfflat",  # TODO: Not in SQLA wrapper, index args: ((features::halfvec(50)) halfvec_l2_ops)
    postgresql_with={"lists": 5000},
)


class ObjectCNNFeaturesVectorBean(Bean):
    """
    A bean for feeding DBWriter.
    """

    def __init__(self, obj_id: ObjectIDT, features: List[float]):
        super().__init__(
            {
                "objcnnid": obj_id,
                "features": features,
            }
        )
