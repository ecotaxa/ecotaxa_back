# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
from BO.User import UserIDT
from DB.Training import Training
from DB.helpers import Session
from helpers import DateTime
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


# noinspection SqlDialectInspection
class TrainingBO(object):
    """
    A training, i.e. the event of producing predictions for lots of objects.
    """

    __slots__ = [
        "_training",
    ]

    def __init__(self, training: Training):
        self._training = training

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a training field somehow then return it"""
        return getattr(self._training, item)

    @classmethod
    def create_one(cls, session: Session, author: UserIDT) -> "TrainingBO":
        trn = Training()
        trn.training_when = DateTime.now_time()
        trn.training_author = author
        trn.training_path = "?"
        session.add(trn)
        session.flush([trn])  # to get the training ID populated
        return TrainingBO(trn)
