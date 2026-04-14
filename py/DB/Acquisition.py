# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, Tuple

# noinspection PyProtectedMember
from sqlalchemy.orm import relationship, Session

from .Project import Project
from .Sample import Sample
from .helpers.DDL import Column, ForeignKey, Index
from .helpers.Direct import text
from .helpers.ORM import Model, desc
from .helpers.Postgres import VARCHAR, BIGINT

ACQUISITION_FREE_COLUMNS = 31

ACQ_PRJ_OFFSET = 10_000_000  # AKA 1e7


class Acquisition(Model):
    # Historical (plural) name of the table
    __tablename__ = "acquisitions"
    # Self ID
    acquisid: int = Column(BIGINT, primary_key=True, autoincrement=False)
    # Parent ID
    acq_sample_id: int = Column(BIGINT, ForeignKey("samples.sampleid"), nullable=False)
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
    def get_next_pk(cls, session: Session, prj_id: int) -> int:
        """
        Return the next available primary key for a new Acquisition in the given project.
        """
        session.execute(text("SELECT pg_advisory_xact_lock(1000, :id)"), {"id": prj_id})
        res = session.query(Acquisition.acquisid)
        res = res.join(Sample)
        res = res.filter(Sample.projid == prj_id)
        res = res.order_by(desc(Acquisition.acquisid)).limit(1).scalar()
        return res + 1 if res else prj_id * ACQ_PRJ_OFFSET + 1

    def set_next_pk(self, session: Session, prj_id: int) -> None:
        """
        Set the next available primary key for this Acquisition instance.
        """
        self.acquisid = self.get_next_pk(session, prj_id)

    @classmethod
    def get_orig_id_and_model(
        cls, session: Session, prj_id
    ) -> Dict[Tuple[str, str], "Acquisition"]:
        """
        Read in memory all Acquisitions for given project and return them indexed by their user-visible
        unique key, AKA parent sample orig_id + self orig_id.
        """
        res = session.query(Acquisition, Sample.orig_id)
        res = res.join(Sample)
        res = res.join(Project)
        res = res.filter(Project.projid == prj_id)
        res = res.order_by(Sample.orig_id, Acquisition.orig_id)
        ret = {(sample_orig_id, r.orig_id): r for r, sample_orig_id in res}
        return ret

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.acquisid)

    def __lt__(self, other):
        return self.acquisid < other.acquisid


for i in range(1, ACQUISITION_FREE_COLUMNS):
    setattr(Acquisition, "t%02d" % i, Column(VARCHAR(250)))

Index(
    "is_acquis_sample_orig_id",
    Acquisition.__table__.c.acq_sample_id,
    Acquisition.__table__.c.orig_id,
    postgresql_include=[
        Acquisition.__table__.c.acquisid
    ],  # For Index Only scans during recursive descent
    unique=True,
)


Index(
    "is_acquis_sample",
    Acquisition.__table__.c.acq_sample_id,
    postgresql_include=[
        Acquisition.__table__.c.acquisid
    ],  # For Index Only scans during recursive descent
    unique=False,
)
