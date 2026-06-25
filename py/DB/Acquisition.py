# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, Tuple, List
from typing import TYPE_CHECKING

from sqlalchemy import func, DDL, event  # fmt: skip
from sqlalchemy.orm import mapped_column

from .helpers.DDL import ForeignKey, Index
from .helpers.Direct import text
from .helpers.ORM import Model, Session, Mapped
from .helpers.Postgres import VARCHAR, BIGINT

# noinspection PyProtectedMember

ACQUISITION_FREE_COLUMNS = 31

if TYPE_CHECKING:
    from .Process import Process
    from .Object import ObjectHeader

from .Project import Project
from .Sample import Sample

ACQ_PRJ_OFFSET = 10_000_000  # AKA 1e7

AcquisitionIDT = int
AcquisitionIDListT = List[
    int
]  # Typings, to be clear that these are not e.g. project IDs
AcquisitionOrigIDT = str


class Acquisition(Model):
    # Historical (plural) name of the table
    __tablename__ = "acquisitions"
    # Self ID
    acquisid: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    # Parent ID
    # TODO: Delete cascade
    acq_sample_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("samples.sampleid", onupdate="CASCADE")
    )
    # i.e. acq_id from TSV
    orig_id: Mapped[str] = mapped_column(VARCHAR(255))
    # TODO: Put into a dedicated table
    instrument: Mapped[str | None] = mapped_column(VARCHAR(255))

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        sample: Mapped[Sample]
        process: Mapped[Process]
        all_objects: Mapped[List[ObjectHeader]]

    def pk(self) -> int:
        return self.acquisid

    @classmethod
    def get_next_pk(cls, session: Session, prj_id: int) -> int:
        """
        Return the next available primary key for a new Acquisition in the given project.
        """
        session.execute(text("SELECT pg_advisory_xact_lock(1000, :id)"), {"id": prj_id})
        res = (
            session.query(func.max(cls.acquisid))
            .filter(cls.acquisid >= prj_id * ACQ_PRJ_OFFSET)
            .filter(cls.acquisid < (prj_id + 1) * ACQ_PRJ_OFFSET)
            .scalar()
        )
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
    setattr(Acquisition, "t%02d" % i, mapped_column(VARCHAR(250)))

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

_create_func_ddl = DDL(f"""
CREATE OR REPLACE FUNCTION acq_in_prj(prj_id int)
RETURNS int8range AS $$
  SELECT int8range(
    prj_id * {ACQ_PRJ_OFFSET}::bigint,
    (prj_id + 1) * {ACQ_PRJ_OFFSET}::bigint,
    '[)'
  );
$$ LANGUAGE sql IMMUTABLE;

GRANT EXECUTE ON FUNCTION acq_in_prj(int) TO PUBLIC;
""")

event.listen(
    Acquisition.__table__,
    "after_create",
    _create_func_ddl.execute_if(dialect="postgresql"),
)
