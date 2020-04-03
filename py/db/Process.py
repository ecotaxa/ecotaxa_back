# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy import Sequence, Column, ForeignKey, Index
from sqlalchemy.dialects.postgresql import BIGINT, VARCHAR, INTEGER
from sqlalchemy.engine import ResultProxy
from sqlalchemy.orm import relationship, Session

from db.Model import Model


class Process(Model):
    # db table
    __tablename__ = 'process'
    processid = Column(BIGINT, Sequence('seq_process'), primary_key=True)
    projid = Column(INTEGER, ForeignKey('projects.projid'))
    project = relationship("Project")
    # i.e. process_id from TSV
    orig_id = Column(VARCHAR(255))

    @staticmethod
    def pk():
        return "processid"

    @classmethod
    def get_orig_id_and_pk(cls, session: Session, prj_id):
        sql = "SELECT orig_id, processid" + \
              "  FROM " + cls.__tablename__ + \
              " WHERE projid = :prj"
        res: ResultProxy = session.execute(sql, {"prj": prj_id})
        ret = {r[0]: int(r[1]) for r in res}
        return ret


def __str__(self):
    return "{0} ({1})".format(self.orig_id, self.processid)


for i in range(1, 31):
    setattr(Process, "t%02d" % i, Column(VARCHAR(250)))
Index('IS_ProcessProject', Process.projid)
