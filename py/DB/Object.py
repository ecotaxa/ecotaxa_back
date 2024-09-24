# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# noinspection PyPackageRequirements
from __future__ import annotations

import datetime
from typing import Dict, Set, Iterable, TYPE_CHECKING

# noinspection PyPackageRequirements
from sqlalchemy import Index, Column, ForeignKey, Sequence, Integer  # fmt:skip
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
)  # fmt:skip
# noinspection PyPackageRequirements
from sqlalchemy.orm import relationship, Session

from BO.helpers.TSVHelpers import convert_degree_minute_float_to_decimal_degree
from .Acquisition import Acquisition
from .Image import Image
from .Project import Project, ProjectIDT
from .Sample import Sample
from .Taxonomy import Taxonomy
from .Training import Training
from .User import User
from .helpers.ORM import Model

# Typings
ObjectIDT = int
if TYPE_CHECKING:
    pass
    # from .Image import Image

# Classification qualification
PREDICTED_CLASSIF_QUAL = "P"  # according to 'training_id' output, the object _might be_ a 'classif_id'. Details of why in related training/predictions.
DUBIOUS_CLASSIF_QUAL = "D"  # 'classif_who' said at 'classif_when' moment that the object is _probably not_ a 'classif_id'
VALIDATED_CLASSIF_QUAL = "V"  # 'classif_who' said at 'classif_when' moment that the object _is_ a 'classif_id'
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
    objid = Column(BIGINT, Sequence("seq_objects"), primary_key=True)  # 8 bytes align d
    # Parent
    acquisid = Column(
        INTEGER, ForeignKey("acquisitions.acquisid", ondelete="CASCADE"), nullable=False
    )  # 4 bytes align i
    # User-visible classification
    classif_id = Column(INTEGER, ForeignKey(Taxonomy.id))  # 4 bytes align i

    # 86400 different values, basically all possible minutes of day
    objtime = Column(TIME)  # 8 bytes align d
    latitude = Column(DOUBLE_PRECISION)  # 8 bytes align d
    longitude = Column(DOUBLE_PRECISION)  # 8 bytes align d
    depth_min = Column(FLOAT)  # AKA DOUBLE_PRECISION, 8 bytes align d
    depth_max = Column(
        FLOAT
    )  # AKA DOUBLE_PRECISION, 8 bytes align d # max = 99999999999 conventional value prevents move to float4
    # _only_ 7018 different values
    objdate = Column(DATE)  # 4 bytes align i
    #
    # One of the *_CLASSIF_QUAL above
    classif_qual = Column(CHAR(1))  # 2 bytes (len + content) align c as len < 127
    #
    sunpos = Column(
        CHAR(1)
    )  # Sun position, from date, time and coords # 2 bytes (len + content) align c as len < 127
    classif_when = Column(TIMESTAMP)  # 8 bytes align d
    classif_who = Column(Integer, ForeignKey(User.id))  # 4 bytes align i

    # If the object is Predicted, the training which produced the prediction(s), current guess is classif_id
    # TODO: Rebuild/Re-shuffle for optimal per-tuple space
    training_id = Column(INTEGER, ForeignKey(Training.training_id))  # 4 bytes align i

    # User-provided identifier
    orig_id = Column(
        VARCHAR(255), nullable=False
    )  # (len+1) bytes, align i if len > 127

    # 176M values in DB as of 2024-02-02
    object_link = Column(VARCHAR(255))

    complement_info = Column(VARCHAR)  # e.g. "Part of ostracoda"

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
        qry = session.query(ObjectHeader.orig_id, ObjectHeader.objid)
        qry = qry.join(Acquisition).join(Sample).join(Project)
        qry = qry.filter(Project.projid == prj_id)
        ret = {orig_id: objid for orig_id, objid in qry}
        return ret

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


USED_FIELDS_FOR_CLASSIF = {  # From user point of view, only these can be changed
    ObjectHeader.classif_qual.name,
    ObjectHeader.classif_id.name,
    ObjectHeader.classif_who.name,
    ObjectHeader.classif_when.name,
}
HIDDEN_FIELDS_FOR_CLASSIF = {  # Internally managed
    ObjectHeader.training_id.name,
}
NON_UPDATABLE_VIA_API = USED_FIELDS_FOR_CLASSIF.union(HIDDEN_FIELDS_FOR_CLASSIF)


class ObjectFields(Model):
    __tablename__ = "obj_field"
    objfid = Column(
        BIGINT, ForeignKey(ObjectHeader.objid, ondelete="CASCADE"), primary_key=True
    )
    # Not a real FK, this is used for a cluster which groups together data blocks by acquisition
    acquis_id = Column(INTEGER, nullable=False)
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship


Index(  # We CLUSTER using this one, object ids tend to be consecutively read
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

# Add free columns, numerical and textual ones
for i in range(1, 501):
    # 8 bytes each, if present
    setattr(ObjectFields, "n%02d" % i, Column(FLOAT))
for i in range(1, 21):
    setattr(ObjectFields, "t%02d" % i, Column(VARCHAR(250)))

# Nearly-always used index for recursive descent into object tree, e.g. in manual classification page.
# Also for FK checks during deletion.
Index(
    "is_objectsacquisition",
    ObjectHeader.__table__.c.acquisid,
)

# Speed up a bit top bar with stats by state.
Index(
    "is_objectsacqclassifqual",
    ObjectHeader.__table__.c.acquisid,
    postgresql_include=[
        ObjectHeader.__table__.c.classif_qual,
        ObjectHeader.__table__.c.classif_id,
    ],
)

# For finding globally objects in some depth range
Index(
    "is_objectsdepth",
    ObjectHeader.__table__.c.depth_max,
    ObjectHeader.__table__.c.depth_min,
    postgresql_include=[ObjectHeader.__table__.c.acquisid],
)
# For finding globally objects in some geo range
Index(
    "is_objectslatlong",
    ObjectHeader.__table__.c.latitude,
    ObjectHeader.__table__.c.longitude,
    postgresql_include=[ObjectHeader.__table__.c.acquisid],
)
# For finding globally objects in some time range
Index(
    "is_objectstime",
    ObjectHeader.__table__.c.objtime,
    postgresql_include=[ObjectHeader.__table__.c.acquisid],
)
Index(
    "is_objectsdate",
    ObjectHeader.__table__.c.objdate,
    postgresql_include=[ObjectHeader.__table__.c.acquisid],
)
# For FK checks during deletion
Index("is_objecttraining", ObjectHeader.__table__.c.training_id)

DEFAULT_CLASSIF_HISTORY_DATE = "TO_TIMESTAMP(0)"


class ObjectsClassifHisto(Model):
    __tablename__ = "objectsclassifhisto"
    objid = Column(
        BIGINT, ForeignKey(ObjectHeader.objid, ondelete="CASCADE"), primary_key=True
    )  # 8 bytes align d
    # Date of manual setting of V or D, training date for P (duplicated from Training for convenience)
    classif_date = Column(TIMESTAMP, primary_key=True)  # 8 bytes align d
    classif_id = Column(
        INTEGER, ForeignKey(Taxonomy.id, ondelete="CASCADE"), nullable=False
    )  # 4 bytes align i, dropped. # TODO: Re-shuffle for optimal per-tuple space
    # classif_type = Column(
    #     CHAR(1)
    # )  # A : Automatic, M : Manual # 2 bytes (len + content) align c as len < 127
    classif_qual = Column(CHAR(1))  # 2 bytes (len + content) align c as len < 127
    classif_who = Column(Integer, ForeignKey(User.id))  # 4 bytes align i
    # The training which caused the P state
    training_id = Column(
        Integer, ForeignKey(Training.training_id, ondelete="CASCADE")
    )  # 4 bytes align i
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship


# For FK checks during deletion
Index("is_objecthistotraining", ObjectsClassifHisto.__table__.c.training_id)
