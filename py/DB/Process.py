# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from .Acquisition import Acquisition
from .helpers.DDL import Column, ForeignKey
from .helpers.ORM import Model
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR, INTEGER

PROCESS_FREE_COLUMNS = 31


class Process(Model):
    # DB table
    __tablename__ = 'process'
    # Twin table with Acquisitions
    processid: int = Column(INTEGER, ForeignKey(Acquisition.acquisid, onupdate="CASCADE", ondelete="CASCADE"),
                            primary_key=True)
    # i.e. process_id from TSV
    orig_id = Column(VARCHAR(255), nullable=False)

    # The relationships are created in Relations.py but the typing here helps IDE
    acquisition: relationship

    def pk(self) -> int:
        return self.processid

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.processid)


for i in range(1, PROCESS_FREE_COLUMNS):
    setattr(Process, "t%02d" % i, Column(VARCHAR(250)))
