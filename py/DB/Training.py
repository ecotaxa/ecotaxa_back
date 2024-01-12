# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A training is an operation which consists in determining, for each of a set of objects,
# the most likely classifications AKA predictions.
# This object is immutable after all children predictions are added. It reflects _what happened_.
# Only exception to this rule is when predicted objects disappear.
#
from datetime import datetime

from sqlalchemy.dialects.postgresql import (
    VARCHAR,
    INTEGER,
    TIMESTAMP,
)

from .Project import Project
from .User import User
from .helpers.DDL import Column, ForeignKey, Index
from .helpers.ORM import Model
from .helpers.ORM import relationship

TrainingIDT = int


class Training(Model):
    __tablename__ = "training"
    # Below, SQLA/Alembic automatically makes column SERIAL, sequence from PG is 'training_training_id_seq'
    training_id: int = Column(INTEGER, primary_key=True)
    # The target project, used only during migration.
    projid: int = Column(
        INTEGER, ForeignKey(Project.projid, ondelete="CASCADE"), nullable=True
    )
    # Who launched or is responsible for the training operation
    training_author: str = Column(INTEGER, ForeignKey(User.id), nullable=False)
    # When it occurred
    training_start: datetime = Column(TIMESTAMP, nullable=False)
    training_end: datetime = Column(TIMESTAMP, nullable=False)
    # The settings used?
    training_path: str = Column(VARCHAR(80), nullable=False)

    # The relationships are created in Relations.py but the typing here helps the IDE
    author: relationship
    predictions: relationship
    project: relationship

    def __str__(self):
        return "Training #{0} by user {1} on the {2}".format(
            self.training_id, self.training_author, self.training_start
        )


Index(
    "trn_projid_start",
    Training.projid,
    Training.training_start,
    unique=True,
)
