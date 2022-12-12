# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from DB.helpers.ORM import Model
from DB.helpers.DDL import Index, Column, Sequence, ForeignKey
from DB.helpers.Postgres import BIGINT, INTEGER, DOUBLE_PRECISION, BOOLEAN


class Prediction(Model):
    __tablename__ = 'predictions'

    pred_id = Column(BIGINT, Sequence('seq_predictions'), primary_key=True)
    object_id = Column(BIGINT, ForeignKey('obj_head.objid', ondelete="CASCADE"), nullable=False)
    classif_id = Column(INTEGER, nullable=False)
    score = Column(DOUBLE_PRECISION, nullable=False)
    discarded = Column(BOOLEAN, nullable=False)

Index("pred_object_id_index", Prediction.object_id)