# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import datetime
from typing import Optional

from BO.User import UserIDT
from DB.Training import Training
from DB.helpers import Session
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


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

    @property
    def training(self) -> Training:
        return self._training

    def advance(self):
        """Mark some progress by updating training_end"""
        self._training.training_end = datetime.now()

    @classmethod
    def create_one(
        cls, session: Session, author: UserIDT, reason: str, training_start: datetime
    ) -> "TrainingBO":
        trn = Training()
        trn.training_start = training_start
        trn.training_end = datetime.fromtimestamp(0)  # In progress
        trn.training_author = author
        trn.training_path = reason
        session.add(trn)
        session.flush([trn])  # to get the training ID populated
        return TrainingBO(trn)

    @classmethod
    def find_by_start_time_or_create(
        cls, session: Session, author: UserIDT, reason: str, start_time: datetime
    ) -> "TrainingBO":
        ret = (
            session.query(Training)
            .filter(Training.training_start == start_time)
            .first()
        )
        if ret is None:
            return cls.create_one(session, author, reason, start_time)
        else:
            return TrainingBO(ret)


class TrainingBOProvider(object):
    """We don't want to create empty trainings, so provide one when we know it will be useful,
    i.e. filled with predictions."""

    def __init__(
        self, session: Session, user_id: UserIDT, reason: str, training_start: datetime
    ):
        self.session: Session = session
        self.user_id = user_id
        self.training_start = training_start
        self.path = reason
        self.current_training: Optional[TrainingBO] = None

    def provide(self) -> TrainingBO:
        if self.current_training is None:
            self.current_training = TrainingBO.find_by_start_time_or_create(
                self.session,
                self.user_id,
                self.path,
                self.training_start,
            )
        return self.current_training
