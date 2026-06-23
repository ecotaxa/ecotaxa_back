# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import TYPE_CHECKING, List

from .helpers.DDL import Column, ForeignKey
from .helpers.ORM import Model, Mapped
from .helpers.Postgres import VARCHAR, BIGINT

if TYPE_CHECKING:
    from .Acquisition import Acquisition

PROCESS_FREE_COLUMNS = 31

ProcessIDT = int
ProcessIDListT = List[int]  # Typings, to be clear that these are not e.g. project IDs
ProcessOrigIDT = str


class Process(Model):
    # DB table
    __tablename__ = "process"
    # Twin table with Acquisitions
    processid: int = Column(
        BIGINT,
        ForeignKey("acquisitions.acquisid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    # i.e. process_id from TSV
    orig_id = Column(VARCHAR(255), nullable=False)

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        acquisition: Mapped[Acquisition]

    def pk(self) -> int:
        return self.processid

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.processid)


for i in range(1, PROCESS_FREE_COLUMNS):
    setattr(Process, "t%02d" % i, Column(VARCHAR(250)))
