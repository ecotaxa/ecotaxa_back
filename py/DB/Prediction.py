# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Generated by a training operation, a prediction associates a class/label predicted
# by an ML algorithm with an object, with a confidence score.
#
from __future__ import annotations

from typing import NamedTuple

from sqlalchemy import PrimaryKeyConstraint

from DB.helpers.DDL import Column, ForeignKey
from DB.helpers.ORM import Model
from DB.helpers.Postgres import BIGINT, INTEGER, DOUBLE_PRECISION
from .Object import ObjectHeader
from .Taxonomy import Taxonomy
from .Training import Training

PSEUDO_TRAINING_SCORE = 1.0


class ClassifScore(NamedTuple):
    classif: int
    score: float


# pg_table_size: 13851295744 of 230M lines using (training_id,object_id,classif_id,score) -> 60 b/tuple
# pg_table_size: 11998306304 of 230M lines using (object_id,training_id,classif_id,score) -> 52 b/tuple
class Prediction(Model):
    __tablename__ = "prediction"

    object_id: int = Column(
        BIGINT,
        ForeignKey(ObjectHeader.objid, ondelete="CASCADE"),
        nullable=False,
    )
    training_id: int = Column(
        INTEGER,
        ForeignKey(Training.training_id, ondelete="CASCADE"),
        nullable=False,
    )
    classif_id: int = Column(
        INTEGER,
        ForeignKey(Taxonomy.id, ondelete="CASCADE"),
        nullable=False,
    )
    score = Column(DOUBLE_PRECISION, nullable=False)  # payload

    # Define the 'normal' PK, from more general to less general, we had to reorder for space
    __table_args__ = (PrimaryKeyConstraint("object_id", "classif_id"),)


class PredictionHisto(Model):
    __tablename__ = "prediction_histo"

    object_id: int = Column(
        BIGINT,
        ForeignKey(ObjectHeader.objid, ondelete="CASCADE"),
        nullable=False,
    )
    training_id: int = Column(
        INTEGER,
        ForeignKey(Training.training_id, ondelete="CASCADE"),
        nullable=False,
    )
    classif_id: int = Column(
        INTEGER,
        ForeignKey(Taxonomy.id, ondelete="CASCADE"),
        nullable=False,
    )
    score = Column(DOUBLE_PRECISION, nullable=False)  # payload

    # Define the 'normal' PK, from more general to less general, we had to reorder for space
    __table_args__ = (PrimaryKeyConstraint("training_id", "object_id", "classif_id"),)