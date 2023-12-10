# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A training is an operation which consists in determining, for each of a set of objects,
# the most likely classifications AKA predictions.
# This object is immutable after all children predictions are added. It reflects _what happened_.
# Only exception to this rule is when predicted objects disappear.
#
from .User import User
from .helpers.DDL import Sequence, Column, ForeignKey, DateTime, Integer
from .helpers.ORM import Model
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR

TrainingIDT = int


class Training(Model):
    __tablename__ = "training"
    training_id = Column(Integer(), Sequence("seq_training"), primary_key=True)
    # Who launched or is responsible for the training operation
    training_author = Column(Integer(), ForeignKey(User.id), nullable=False)
    # When it occurred
    training_when = Column(DateTime(), nullable=False)
    # The settings used?
    training_path = Column(VARCHAR(80), nullable=False)

    # The relationships are created in Relations.py but the typing here helps the IDE
    author: relationship
    predictions: relationship

    def __str__(self):
        return "{0} by {1} on the {2}".format(
            self.training_id, self.training_author, self.training_when
        )
