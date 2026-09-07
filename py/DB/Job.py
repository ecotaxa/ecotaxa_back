# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Sequence, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER
from sqlalchemy.orm import mapped_column

from .helpers.ORM import Model, Mapped

# Typings, to be clear that these are not e.g. task IDs
JobIDT = int

if TYPE_CHECKING:
    from .User import User


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
    id: Mapped[int] = mapped_column(
        INTEGER, Sequence("seq_temp_tasks"), primary_key=True
    )
    """ Unique identifier, from a sequence """
    owner_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("users.id"))
    """ The user who created and thus owns the job """
    type: Mapped[str] = mapped_column(VARCHAR(80))
    """ The job type, e.g. import, export... """
    params: Mapped[str | None] = mapped_column(VARCHAR())
    """ JSON-encoded startup parameters """
    state: Mapped[str | None] = mapped_column(VARCHAR(1))
    """ What the job is doing """
    step: Mapped[int | None] = mapped_column(INTEGER)
    """ Where in the workflow the job is """
    progress_pct: Mapped[int | None] = mapped_column(INTEGER)
    """ The progress percentage for UI """
    progress_msg: Mapped[str | None] = mapped_column(VARCHAR())
    """ The message for UI, short version """
    messages: Mapped[str | None] = mapped_column(VARCHAR())
    """ The messages for UI, long version """
    inside: Mapped[str | None] = mapped_column(VARCHAR())
    """ JSON-encoded internal state, to use b/w steps """
    question: Mapped[str | None] = mapped_column(VARCHAR())
    """ JSON-encoded last question data """
    reply: Mapped[str | None] = mapped_column(VARCHAR())
    """ JSON-encoded reply to last question """
    result: Mapped[str | None] = mapped_column(VARCHAR())
    """ JSON-encoded execution result """
    creation_date: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_on: Mapped[datetime] = mapped_column(TIMESTAMP)
    """ Last time that anything changed in present line """

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        owner: Mapped[User]

    def __str__(self):
        return "{0} ({1}): {2}/{3}".format(
            self.id, self.type, self.owner_id, self.params
        )
