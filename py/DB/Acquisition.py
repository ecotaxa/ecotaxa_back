# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, Tuple

# noinspection PyProtectedMember
from sqlalchemy.orm import relationship, Session

from .Project import Project
from .Sample import Sample
from .helpers.DDL import Column, ForeignKey, Sequence, Index
from .helpers.ORM import Model
from .helpers.Postgres import VARCHAR, INTEGER

ACQUISITION_FREE_COLUMNS = 31


class Acquisition(Model):
    # Historical (plural) name of the table
    __tablename__ = "acquisitions"
    # Self ID
    acquisid: int = Column(INTEGER, Sequence("seq_acquisitions"), primary_key=True)
    # Parent ID
    acq_sample_id: int = Column(INTEGER, ForeignKey("samples.sampleid"), nullable=False)
    # i.e. acq_id from TSV
    orig_id: str = Column(VARCHAR(255), nullable=False)
    # TODO: Put into a dedicated table
    instrument = Column(VARCHAR(255))

    # The relationships are created in Relations.py but the typing here helps IDE
    sample: relationship
    process: relationship
    all_objects: relationship

    def pk(self) -> int:
        return self.acquisid

    @classmethod
    def get_orig_id_and_model(
        cls, session: Session, prj_id
    ) -> Dict[Tuple[str, str], "Acquisition"]:
        res = session.query(Acquisition, Sample.orig_id)
        res = res.join(Sample)
        res = res.join(Project)
        res = res.filter(Project.projid == prj_id)
        ret = {(sample_orig_id, r.orig_id): r for r, sample_orig_id in res}
        return ret

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.acquisid)

    def __lt__(self, other):
        return self.acquisid < other.acquisid


for i in range(1, ACQUISITION_FREE_COLUMNS):
    setattr(Acquisition, "t%02d" % i, Column(VARCHAR(250)))

Index("IS_AcquisOrigId", Acquisition.acq_sample_id, Acquisition.orig_id, unique=True)
