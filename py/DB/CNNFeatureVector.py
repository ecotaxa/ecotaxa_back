# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2022-2024 LOVNOWER : Amblard, Colin, Irisson, Reutenauer (UPMC-CNRS-FOTONOWER)
#
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import mapped_column
from sqlalchemy import text

from .helpers.DDL import ForeignKey, Index
from .helpers.ORM import Mapped, Model
from .helpers.Postgres import BIGINT

if TYPE_CHECKING:
    from .Object import ObjectHeader

N_DEEP_FEATURES = 50


class ObjectCNNFeatureVector(Model):
    __tablename__ = "obj_cnn_features_vector"
    objcnnid: Mapped[int] = mapped_column(
        BIGINT,
        ForeignKey("obj_head.objid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    features: Mapped[Vector] = mapped_column(Vector(N_DEEP_FEATURES))
    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        object: Mapped[ObjectHeader]


Index(
    "obj_cnn_features_vector_hv_ivfflat_l2_5k_idx",
    text("((features)::halfvec(50)) halfvec_l2_ops"),
    postgresql_using="ivfflat",
    postgresql_with={"lists": 5000},
)
