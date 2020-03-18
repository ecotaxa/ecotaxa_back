# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy import Index, Column, ForeignKey, Sequence
from sqlalchemy.dialects.postgresql import BIGINT, VARCHAR, INTEGER
from sqlalchemy.orm import relationship

from db.Model import Model


class Acquisition(Model):
    # Historical (plural) name of the table
    __tablename__ = 'acquisitions'
    acquisid = Column(BIGINT, Sequence('seq_acquisitions'), primary_key=True)
    projid = Column(INTEGER, ForeignKey('projects.projid'))
    project = relationship("Project")
    # i.e. acq_id from TSV
    orig_id = Column(VARCHAR(255))
    instrument = Column(VARCHAR(255))

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.acquisid)


for i in range(1, 31):
    setattr(Acquisition, "t%02d" % i, Column(VARCHAR(250)))
Index('IS_AcquisitionsProject', Acquisition.projid)
