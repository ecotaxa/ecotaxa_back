# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A prediction associates a class/label predicted by an ML algorithm to an object.
# Each prediction has a confidence score and a boolean "discarded" attribute, automatically set to True if a user
# indicated that the object does not belong to the predicted class.
#
from __future__ import annotations

from DB.helpers.DDL import Index, Column, Sequence, ForeignKey
from DB.helpers.ORM import Model
from DB.helpers.Postgres import BIGINT, INTEGER, DOUBLE_PRECISION, BOOLEAN


class Prediction(Model):
    __tablename__ = "predictions"

    pred_id = Column(INTEGER, Sequence("seq_predictions"), primary_key=True)
    object_id = Column(
        BIGINT, ForeignKey("obj_head.objid", ondelete="CASCADE"), nullable=False
    )
    score = Column(DOUBLE_PRECISION, nullable=False)
    classif_id = Column(
        INTEGER, ForeignKey("taxonomy.id", ondelete="CASCADE"), nullable=False
    )
    discarded = Column(BOOLEAN, nullable=False)


Index("pred_object_id_index", Prediction.object_id)
