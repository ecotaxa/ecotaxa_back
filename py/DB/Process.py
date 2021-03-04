# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER
# noinspection PyProtectedMember
from sqlalchemy.orm import relationship, Session

from .Acquisition import Acquisition
from .Project import Project
from .Sample import Sample
from .helpers.ORM import Model, Query

PROCESS_FREE_COLUMNS = 31


class Process(Model):
    # DB table
    __tablename__ = 'process'
    # Twin table with Acquisitions
    processid = Column(INTEGER, ForeignKey(Acquisition.acquisid, onupdate="CASCADE", ondelete="CASCADE"),
                       primary_key=True)
    # i.e. process_id from TSV
    orig_id = Column(VARCHAR(255), nullable=False)

    # The relationships are created in Relations.py but the typing here helps IDE
    acquisition: relationship

    def pk(self) -> int:
        return self.processid

    @classmethod
    def get_orig_id_and_model(cls, session: Session, prj_id) -> Dict[str, 'Process']:
        res: Query = session.query(Process)
        res = res.join(Acquisition)
        res = res.join(Sample)
        res = res.join(Project)
        res = res.filter(Project.projid == prj_id)
        ret = {r.orig_id: r for r in res}
        return ret

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.processid)


for i in range(1, PROCESS_FREE_COLUMNS):
    setattr(Process, "t%02d" % i, Column(VARCHAR(250)))
