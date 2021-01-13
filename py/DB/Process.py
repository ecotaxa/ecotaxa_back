# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict

from sqlalchemy import Column, ForeignKey, Index
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER
# noinspection PyProtectedMember
from sqlalchemy.orm import relationship, Session

from DB.helpers.ORM import Model

PROCESS_FREE_COLUMNS = 31


class Process(Model):
    # DB table
    __tablename__ = 'process'
    # Twin table with Acquisitions
    processid = Column(INTEGER, primary_key=True)
    projid = Column(INTEGER, ForeignKey('projects.projid'))
    # i.e. process_id from TSV
    orig_id = Column(VARCHAR(255), nullable=False)

    # The relationships are created in Relations.py but the typing here helps IDE
    project: relationship
    all_objects: relationship

    @staticmethod
    def pk_col():  # pragma: no cover
        # TODO: Not needed anymore but mypy complains
        return "processid"

    def pk(self) -> int:
        return self.processid

    @classmethod
    def get_orig_id_and_model(cls, session: Session, prj_id) -> Dict[str, 'Process']:
        res = session.query(Process).filter(Process.projid == prj_id)
        # sql = "SELECT orig_id, processid" + \
        #       "  FROM " + cls.__tablename__ + \
        #       " WHERE projid = :prj"
        # res: ResultProxy = session.execute(sql, {"prj": prj_id})
        # ret = {r[0]: int(r[1]) for r in res}
        ret = {r.orig_id: r for r in res}
        return ret

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.processid)


for i in range(1, PROCESS_FREE_COLUMNS):
    setattr(Process, "t%02d" % i, Column(VARCHAR(250)))
Index('IS_ProcessProject', Process.projid)
