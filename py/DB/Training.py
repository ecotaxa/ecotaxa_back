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
from typing import TYPE_CHECKING, List

from sqlalchemy.dialects.postgresql import (
    VARCHAR,
    INTEGER,
    TIMESTAMP,
)
from sqlalchemy.orm import mapped_column

from .helpers.DDL import ForeignKey, Index
from .helpers.ORM import Mapped
from .helpers.ORM import Model

if TYPE_CHECKING:
    from .User import User
    from .Prediction import Prediction
    from .Project import Project

TrainingIDT = int
IN_PROGRESS_DATE = datetime.fromtimestamp(0)


class Training(Model):
    __tablename__ = "training"
    # Below, SQLA/Alembic automatically makes column SERIAL, sequence from PG is 'training_training_id_seq'
    training_id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    # The target project.
    projid: Mapped[int | None] = mapped_column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE")
    )
    # Who launched or is responsible for the training operation
    training_author: Mapped[int] = mapped_column(INTEGER, ForeignKey("users.id"))
    # When it occurred
    training_start: Mapped[datetime] = mapped_column(TIMESTAMP)
    training_end: Mapped[datetime] = mapped_column(TIMESTAMP)
    # The settings used?
    training_path: Mapped[str] = mapped_column(VARCHAR(80))

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        author: Mapped[User]
        predictions: Mapped[List[Prediction]]
        project: Mapped[Project]

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
