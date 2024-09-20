# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum

from sqlalchemy import Sequence, Column, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER
from sqlalchemy.orm import relationship

from .helpers.ORM import Model

# Typings, to be clear that these are not e.g. task IDs
JobIDT = int


class DBJobStateEnum(str, Enum):
    Pending = "P"  # Waiting for an execution thread
    Running = "R"  # Being executed inside a thread
    Asking = "A"  # Needing user information before resuming
    Error = "E"  # Stopped with error
    Finished = "F"  # Done


class Job(Model):
    """
    Description of long-running processing operations, back-end side.
    The jobs might need to communicate with the UI for getting input.
    A job db row does not _always_ have a corresponding thread:
        - When it's pending, no associated thread.
        - When it's in question mode, no associated thread either.
        - When done or in error, no thread.
    """

    __tablename__ = "job"
    # Starting 2024 Feb 02, we archive jobs by negating their ids
    id: int = Column(INTEGER, Sequence("seq_temp_tasks"), primary_key=True)
    """ Unique identifier, from a sequence """
    owner_id: int = Column(INTEGER, ForeignKey("users.id"), nullable=False)
    """ The user who created and thus owns the job """
    type: str = Column(VARCHAR(80), nullable=False)
    """ The job type, e.g. import, export... """
    params = Column(VARCHAR())
    """ JSON-encoded startup parameters """
    state = Column(VARCHAR(1))
    """ What the job is doing """
    step = Column(INTEGER)
    """ Where in the workflow the job is """
    progress_pct = Column(INTEGER)
    """ The progress percentage for UI """
    progress_msg = Column(VARCHAR())
    """ The message for UI, short version """
    messages = Column(VARCHAR())
    """ The messages for UI, long version """
    inside = Column(VARCHAR())
    """ JSON-encoded internal state, to use b/w steps """
    question = Column(VARCHAR())
    """ JSON-encoded last question data """
    reply = Column(VARCHAR())
    """ JSON-encoded reply to last question """
    result = Column(VARCHAR())
    """ JSON-encoded execution result """
    creation_date = Column(TIMESTAMP, nullable=False)
    updated_on = Column(TIMESTAMP, nullable=False)
    """ Last time that anything changed in present line """

    owner: relationship

    def __str__(self):
        return "{0} ({1}): {2}/{3}".format(
            self.id, self.type, self.owner_id, self.params
        )
