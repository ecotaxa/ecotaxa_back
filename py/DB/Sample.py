# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict

from sqlalchemy import func

from .Project import Project, ProjectIDT
from .helpers import Result
from .helpers.DDL import Index, Column, ForeignKey
from .helpers.Direct import text
from .helpers.Hints import RECURS_HINT
from .helpers.ORM import Model, relationship, Session
from .helpers.Postgres import VARCHAR, DOUBLE_PRECISION, INTEGER, BIGINT

SAMPLE_FREE_COLUMNS = 61

SAM_PRJ_OFFSET = 1_000_000  # AKA 1e6


class Sample(Model):
    # Historical (plural) name of the table
    __tablename__ = "samples"
    sampleid: int = Column(BIGINT, primary_key=True, autoincrement=False)
    projid: int = Column(
        INTEGER, ForeignKey("projects.projid", onupdate="CASCADE"), nullable=False
    )
    # i.e. sample_id from TSV
    orig_id: str = Column(VARCHAR(255), nullable=False)
    latitude = Column(DOUBLE_PRECISION)
    longitude = Column(DOUBLE_PRECISION)
    dataportal_descriptor = Column(VARCHAR(8000))

    # The relationships are created in Relations.py but the typing here helps IDE
    project: Project
    all_acquisitions: relationship

    def pk(self) -> int:
        return self.sampleid

    @classmethod
    def get_next_pk(cls, session: Session, prj_id: ProjectIDT) -> int:
        """
        Return the next available primary key for a new Sample in the given project.
        """
        session.execute(text("SELECT pg_advisory_xact_lock(1001, :id)"), {"id": prj_id})
        res = (
            session.query(func.max(cls.sampleid))
            .filter(cls.sampleid >= prj_id * SAM_PRJ_OFFSET)
            .filter(cls.sampleid < (prj_id + 1) * SAM_PRJ_OFFSET)
            .scalar()
        )
        return res + 1 if res else prj_id * SAM_PRJ_OFFSET + 1

    def set_next_pk(self, session: Session, prj_id: ProjectIDT) -> None:
        """
        Set the next available primary key for this Sample instance.
        """
        self.sampleid = self.get_next_pk(session, prj_id)

    @classmethod
    def get_orig_id_and_model(
        cls, session: Session, prj_id: ProjectIDT
    ) -> Dict[str, "Sample"]:
        """
        Read in memory all Samples for given project and return them indexed by their user-visible
        unique key, AKA orig_id, in order.
        """
        res = session.query(Sample)
        res = res.join(Project)
        res = res.filter(Project.projid == prj_id)
        res = res.order_by(Sample.orig_id)
        ret = {r.orig_id: r for r in res}
        return ret

    @staticmethod
    def propagate_geo(session: Session, prj_id: ProjectIDT) -> None:
        """
            Create sample geo from objects one.
        TODO: Should be in a BO
        """
        sql = text(
            f"""
        UPDATE samples usam
           SET latitude = sll.latitude, longitude = sll.longitude
          FROM (SELECT {RECURS_HINT} sam.sampleid, MIN(obh.latitude) latitude, MIN(obh.longitude) longitude
                  FROM obj_head obh
                  JOIN acquisitions acq on acq.acquisid = obh.acquisid
                  JOIN samples sam on sam.sampleid = acq.acq_sample_id
                 WHERE sam.projid = :projid
                   AND obh.latitude IS NOT NULL
                   AND obh.longitude IS NOT NULL
                   AND obh.objid <@ obj_in_prj(:projid)
              GROUP BY sam.sampleid) sll
         WHERE usam.sampleid = sll.sampleid
           AND projid = :projid """
        )
        session.execute(sql, {"projid": prj_id})
        session.commit()

    @classmethod
    def get_sample_summary(cls, session: Session, sample_id: int) -> List:
        sql = text(
            f"""
            SELECT {RECURS_HINT} MIN(obh.objdate+obh.objtime), MAX(obh.objdate+obh.objtime), MIN(obh.depth_min), MAX(obh.depth_max)
              FROM obj_head obh
              JOIN acquisitions acq on acq.acquisid = obh.acquisid
              JOIN samples sam on sam.sampleid = acq.acq_sample_id
             WHERE sam.sampleid = :smp """
        )
        res: Result = session.execute(sql, {"smp": sample_id})
        return [a_val for a_val in res.one()]

    def __str__(self):
        return "{0} ({1})".format(self.orig_id, self.sampleid)

    def __lt__(self, other):
        return self.sampleid < other.sampleid


for i in range(1, SAMPLE_FREE_COLUMNS):
    setattr(Sample, "t%02d" % i, Column(VARCHAR(250)))

Index(
    "is_samples_project_orig_id",
    Sample.__table__.c.projid,
    Sample.__table__.c.orig_id,
    postgresql_include=[
        Sample.__table__.c.sampleid
    ],  # For Index Only scans during recursive descent
    unique=True,
)

Index(
    "is_samples_project",
    Sample.__table__.c.projid,
    postgresql_include=[
        Sample.__table__.c.sampleid
    ],  # For Index Only scans during recursive descent
    unique=False,
)
