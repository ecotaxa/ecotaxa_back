# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A prediction associates a class/label predicted by an ML algorithm to an object.
# Each prediction has a confidence score and a boolean "discarded" attribute, set to True if a user
# indicated that the object does not belong to the predicted class.
#
from __future__ import annotations

from DB.helpers.DDL import Index, Column, Sequence, ForeignKey, Boolean
from DB.helpers.ORM import Model
from DB.helpers.Postgres import BIGINT, INTEGER, DOUBLE_PRECISION
from .Object import ObjectHeader


class Prediction(Model):
    __tablename__ = "prediction"

    pred_id = Column(
        INTEGER, Sequence("seq_prediction"), primary_key=True
    )  # TODO: Old design, to replace
    object_id = Column(
        BIGINT, ForeignKey(ObjectHeader.objid, ondelete="CASCADE"), nullable=False
    )
    score = Column(DOUBLE_PRECISION, nullable=False)
    classif_id = Column(
        INTEGER, ForeignKey("taxonomy.id", ondelete="CASCADE"), nullable=False
    )
    discarded = Column(Boolean(), nullable=False)


Index("pred_object_id_index", Prediction.object_id)
