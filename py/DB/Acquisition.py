# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict

from sqlalchemy import Index, Column, ForeignKey, Sequence
from sqlalchemy.dialects.postgresql import BIGINT, VARCHAR, INTEGER
# noinspection PyProtectedMember
from sqlalchemy.orm import relationship, Session

from DB.helpers.ORM import Model

ACQUISITION_FREE_COLUMNS = 31

class Acquisition(Model):
    # Historical (plural) name of the table
    __tablename__ = 'acquisitions'
    acquisid = Column(BIGINT, Sequence('seq_acquisitions'), primary_key=True)
    projid = Column(INTEGER, ForeignKey('projects.projid'))
    # i.e. acq_id from TSV
    orig_id = Column(VARCHAR(255))
    # TODO: Put into a dedicated table
    instrument = Column(VARCHAR(255))

    # The relationships are created in Relations.py but the typing here helps IDE
    project: relationship
    all_objects: relationship
    all_processes: relationship

    @staticmethod
    def pk_col():
        return "acquisid"

    def pk(self) -> int:
        return self.acquisid

    @classmethod
    def get_orig_id_and_model(cls, session: Session, prj_id) -> Dict[str, 'Acquisition']:
        res = session.query(Acquisition).filter(Acquisition.projid == prj_id)
        # sql = "SELECT orig_id, acquisid" + \
        #       "  FROM " + cls.__tablename__ + \
        #       " WHERE projid = :prj"
        # res: ResultProxy = session.execute(sql, {"prj": prj_id})
        # ret = {r[0]: int(r[1]) for r in res}
        ret = {r.orig_id: r for r in res}
        return ret

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.acquisid)


for i in range(1, ACQUISITION_FREE_COLUMNS):
    setattr(Acquisition, "t%02d" % i, Column(VARCHAR(250)))
Index('IS_AcquisitionsProject', Acquisition.projid)
