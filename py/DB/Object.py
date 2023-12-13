# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# noinspection PyPackageRequirements
from __future__ import annotations

import datetime
from typing import Dict, Set, Iterable, TYPE_CHECKING

# noinspection PyPackageRequirements
from sqlalchemy import (
    Index,
    Column,
    ForeignKey,
    Sequence,
    Integer,
)
# noinspection PyPackageRequirements
from sqlalchemy.dialects.postgresql import (
    BIGINT,
    VARCHAR,
    INTEGER,
    DOUBLE_PRECISION,
    DATE,
    TIME,
    FLOAT,
    CHAR,
    TIMESTAMP,
)
# noinspection PyPackageRequirements
from sqlalchemy.orm import relationship, Session

from BO.helpers.TSVHelpers import convert_degree_minute_float_to_decimal_degree
from .Acquisition import Acquisition
from .Image import Image
from .Project import Project, ProjectIDT
from .Sample import Sample
from .Taxonomy import Taxonomy
from .Training import Training
from .helpers import Result
from .helpers.Direct import text
from .helpers.ORM import Model

# Typings
ObjectIDT = int
if TYPE_CHECKING:
    pass
    # from .Image import Image

# Classification qualification
PREDICTED_CLASSIF_QUAL = (
    "P"  # according to 'training_id' output, the object might be a 'classif_id'
)
DUBIOUS_CLASSIF_QUAL = "D"  # 'classif_who' said at 'classif_when' moment that the object is _probably not_ a 'classif_id'
VALIDATED_CLASSIF_QUAL = "V"  # 'classif_who' said at 'classif_when' moment that the object _is_ a 'classif_id'
# TODO: For below, can it ever be seen in object, or always in history?
DISCARDED_CLASSIF_QUAL = "X"  # 'classif_who' said at 'classif_when' moment that the object _is not_ a 'classif_id'
classif_qual_labels = {
    PREDICTED_CLASSIF_QUAL: "predicted",
    DUBIOUS_CLASSIF_QUAL: "dubious",
    VALIDATED_CLASSIF_QUAL: "validated",
    DISCARDED_CLASSIF_QUAL: "discarded",
}
CLASSIF_QUALS = set(classif_qual_labels.keys())
classif_qual_revert = {}
for k, v in classif_qual_labels.items():
    classif_qual_revert[v] = k


class ObjectHeader(Model):
    __tablename__ = "obj_head"
    # Self
    objid = Column(BIGINT, Sequence("seq_objects"), primary_key=True)
    # Parent
    acquisid = Column(
        INTEGER, ForeignKey("acquisitions.acquisid", ondelete="CASCADE"), nullable=False
    )
    # User-provided identifier
    orig_id = Column(VARCHAR(255), nullable=False)

    objdate = Column(DATE)
    objtime = Column(TIME)

    latitude = Column(DOUBLE_PRECISION)
    longitude = Column(DOUBLE_PRECISION)
    depth_min = Column(FLOAT)
    depth_max = Column(FLOAT)
    #
    sunpos = Column(CHAR(1))  # Sun position, from date, time and coords

    # The displayed (to users) classification
    classif_id = Column(INTEGER)
    # The following is logically out of this block of 4, because depending on its value,
    # - it's the other classif_* columns which reflecting the "last state"
    # - or the classif_auto_* ones.
    classif_qual = Column(CHAR(1))
    classif_who = Column(Integer, ForeignKey("users.id"))
    # Date the current other classif_* were last set
    classif_when = Column(TIMESTAMP)

    # If the object was ever predicted, the last training which produced the predictions
    training_id = Column(INTEGER, ForeignKey(Training.training_id))

    # classif_crossvalidation_id = Column(
    #     INTEGER
    # )  # Always NULL in prod', verified 02/12/2023

    complement_info = Column(VARCHAR)  # e.g. "Part of ostracoda"

    # similarity = Column(DOUBLE_PRECISION)  # Always NULL in prod', verified 02/12/2023

    # TODO: Why random? It makes testing a bit more difficult
    random_value = Column(INTEGER)

    # 72832 unique values as of 02/12/2023
    object_link = Column(VARCHAR(255))

    # Below is not true if not Predicted or Validated, left here for reference
    # ForeignKeyConstraint(
    #     ["training_id", "objid", "classif_id"],
    #     ["Prediction.training_id", "Prediction.object_id", "Prediction.classif_id"],
    #     name="obj2pred",
    # )

    # The relationships are created in Relations.py but the typing here helps the IDE
    fields: ObjectFields
    cnn_features: relationship
    classif: relationship
    classif_auto: relationship
    classifier: relationship
    all_images: Iterable[Image]
    acquisition: relationship
    history: relationship
    last_training: relationship

    @classmethod
    def fetch_existing_objects(
        cls, session: Session, prj_id: ProjectIDT
    ) -> Dict[str, int]:
        # TODO: Why using the view?
        sql = text(
            "SELECT o.orig_id, o.objid " "  FROM objects o " " WHERE o.projid = :prj"
        )
        res: Result = session.execute(sql, {"prj": prj_id})
        ret = {orig_id: objid for orig_id, objid in res}
        return ret  # type: ignore

    @classmethod
    def fetch_existing_ranks(cls, session: Session, prj_id) -> Dict[int, Set[int]]:
        ret: Dict[int, Set[int]] = {}
        qry = session.query(Image.objid, Image.imgrank)
        qry = qry.join(ObjectHeader).join(Acquisition).join(Sample).join(Project)
        qry = qry.filter(Project.projid == prj_id)
        for objid, imgrank in qry:
            ret.setdefault(objid, set()).add(imgrank)
        return ret

    @staticmethod
    def _geo_from_txt(txt: str, min_v: float, max_v: float) -> float:
        """Convert/check latitude or longitude before setting field
        :raises ValueError"""
        ret = convert_degree_minute_float_to_decimal_degree(txt)
        if ret is None:
            raise ValueError
        if ret < min_v or ret > max_v:
            raise ValueError
        return ret

    @staticmethod
    def latitude_from_txt(txt: str) -> float:
        return ObjectHeader._geo_from_txt(txt, -90, 90)

    @staticmethod
    def longitude_from_txt(txt: str) -> float:
        return ObjectHeader._geo_from_txt(txt, -180, 180)

    @staticmethod
    def depth_from_txt(txt: str) -> float:
        """Convert depth before setting field
        :raises ValueError"""
        return float(txt)

    @staticmethod
    def time_from_txt(txt: str) -> datetime.time:
        """Convert/check time before setting field. HHMM with optional SS. Or strictly HH:MM:SS
        :raises ValueError"""
        if txt[2:3] == txt[5:6] == ":":
            return datetime.time(int(txt[0:2]), int(txt[3:5]), int(txt[6:8]))
        # Left pad with 0s as they tend to be truncated by spreadsheets e.g. 320 -> 0320
        txt = "0" * (4 - len(txt)) + txt if len(txt) < 4 else txt
        # Right pad with 0s for seconds e.g. 0320 -> 032000
        txt += "0" * (6 - len(txt)) if len(txt) < 6 else ""
        return datetime.time(int(txt[0:2]), int(txt[2:4]), int(txt[4:6]))

    @staticmethod
    def date_from_txt(txt: str) -> datetime.date:
        """Convert/check date before setting field. Format YYYYMMDD or YYYY-MM-DD
        :raises ValueError"""
        if txt[4:5] == txt[7:8] == "-":
            return datetime.date(int(txt[0:4]), int(txt[5:7]), int(txt[8:10]))
        return datetime.date(int(txt[0:4]), int(txt[4:6]), int(txt[6:8]))

    def __lt__(self, other):
        return self.objid < other.objid


class ObjectFields(Model):
    __tablename__ = "obj_field"
    objfid = Column(
        BIGINT, ForeignKey(ObjectHeader.objid, ondelete="CASCADE"), primary_key=True
    )
    # Not a real FK, this is used for a cluster which groups together data blocks by acquisition
    acquis_id = Column(INTEGER, nullable=True)
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship


Index(
    "obj_field_acquisid_objfid_idx",
    ObjectFields.__table__.c.acquis_id,
    ObjectFields.__table__.c.objfid,
)

# TODO
# event.listen(
#     ObjectsFields.__table__,
#     "after_create",
#     DDL("ALTER TABLE obj_field SET (fillfactor = 90, statistics_target = 10000)"
#         ).execute_if(dialect='postgresql')
# )

# Ajout des colonnes numériques & textuelles libres
for i in range(1, 501):
    # 8 bytes each, if present
    setattr(ObjectFields, "n%02d" % i, Column(FLOAT))
for i in range(1, 21):
    setattr(ObjectFields, "t%02d" % i, Column(VARCHAR(250)))

Index(
    "is_objectsacqclassifqual",
    ObjectHeader.__table__.c.acquisid,
    ObjectHeader.__table__.c.classif_id,
    ObjectHeader.__table__.c.classif_qual,
)
Index(
    "is_objectsacqrandom",
    ObjectHeader.__table__.c.acquisid,
    ObjectHeader.__table__.c.random_value,
    ObjectHeader.__table__.c.classif_qual,
)
Index(
    "is_objectsdepth",
    ObjectHeader.__table__.c.depth_max,
    ObjectHeader.__table__.c.depth_min,
    ObjectHeader.__table__.c.acquisid,
)
Index(
    "is_objectslatlong",
    ObjectHeader.__table__.c.latitude,
    ObjectHeader.__table__.c.longitude,
)
Index(
    "is_objectstime",
    ObjectHeader.__table__.c.objtime,
    ObjectHeader.__table__.c.acquisid,
)
Index(
    "is_objectsdate",
    ObjectHeader.__table__.c.objdate,
    ObjectHeader.__table__.c.acquisid,
)
# For FK checks during deletion
Index("is_objectsacquisition", ObjectHeader.__table__.c.acquisid)

DEFAULT_CLASSIF_HISTORY_DATE = "TO_TIMESTAMP(0)"


class ObjectsClassifHisto(Model):
    __tablename__ = "objectsclassifhisto"
    objid = Column(
        BIGINT, ForeignKey("obj_head.objid", ondelete="CASCADE"), primary_key=True
    )
    # The date, set if manual action
    classif_date = Column(TIMESTAMP, primary_key=True)
    # classif_type = Column(CHAR(1))  # A : Automatic, M : Manual
    classif_id = Column(INTEGER, ForeignKey(Taxonomy.id, ondelete="CASCADE"))
    classif_qual = Column(CHAR(1))  # 'P', 'V', 'D' + 'X' for discarded
    classif_who = Column(Integer, ForeignKey("users.id"))  # The user who did the action
    training_id = Column(
        INTEGER, ForeignKey(Training.training_id, ondelete="CASCADE")
    )  # The training causing the values

    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship
