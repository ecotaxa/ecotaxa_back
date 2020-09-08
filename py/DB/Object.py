# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# noinspection PyPackageRequirements
import datetime
from typing import Dict

# noinspection PyPackageRequirements
from sqlalchemy import Index, Column, ForeignKey, Sequence, Integer
# noinspection PyPackageRequirements
from sqlalchemy.dialects.postgresql import BIGINT, VARCHAR, INTEGER, REAL, DOUBLE_PRECISION, DATE, TIME, FLOAT, CHAR, \
    TIMESTAMP
# noinspection PyPackageRequirements,PyProtectedMember
from sqlalchemy.engine import ResultProxy
# noinspection PyPackageRequirements
from sqlalchemy.orm import relationship, Session

from BO.helpers.TSVHelpers import convert_degree_minute_float_to_decimal_degree
# noinspection PyUnresolvedReferences
from .Taxonomy import Taxonomy
# noinspection PyUnresolvedReferences
from .User import User
from .helpers.ORM import Model

# Classification qualification
classif_qual = {'P': 'predicted', 'D': 'dubious', 'V': 'validated'}
classif_qual_revert = {}
for (k, v) in classif_qual.items():
    classif_qual_revert[v] = k


# TODO: SQLAlchemy uses nextval(seq) in the generated SQL
#  It's probably possible that the seq is used server-side and not needed in client SQL
#   Python side: Sequence('seq_objects', optional=True)
#   Server-side: SERIAL/IDENTITY/Trigger?
class ObjectHeader(Model):
    __tablename__ = 'obj_head'
    objid = Column(BIGINT, Sequence('seq_objects'), primary_key=True)

    projid = Column(INTEGER, ForeignKey('projects.projid'), nullable=False)

    #
    objdate = Column(DATE)
    objtime = Column(TIME)

    latitude = Column(DOUBLE_PRECISION)
    longitude = Column(DOUBLE_PRECISION)
    depth_min = Column(FLOAT)
    depth_max = Column(FLOAT)
    #
    sunpos = Column(CHAR(1))  # Sun position, from date, time and coords
    #
    classif_id = Column(INTEGER)
    classif_qual = Column(CHAR(1))
    classif_who = Column(Integer, ForeignKey('users.id'))
    classif_when = Column(TIMESTAMP)

    classif_auto_id = Column(INTEGER)
    classif_auto_score = Column(DOUBLE_PRECISION)
    classif_auto_when = Column(TIMESTAMP)

    classif_crossvalidation_id = Column(INTEGER)
    #
    # The _first_ image
    # Relation b/w next images and present Object are in Image.objid
    # TODO: WTF, normalize.
    img0id = Column(BIGINT)
    imgcount = Column(INTEGER)
    complement_info = Column(VARCHAR)

    similarity = Column(DOUBLE_PRECISION)

    # TODO: Why random? It makes testing a bit more difficult
    random_value = Column(INTEGER)

    sampleid = Column(INTEGER, ForeignKey('samples.sampleid'))
    acquisid = Column(INTEGER, ForeignKey('acquisitions.acquisid'))
    processid = Column(INTEGER, ForeignKey('process.processid'))

    # The relationships are created in Relations.py but the typing here helps the IDE
    project: relationship
    fields: relationship
    cnn_features: relationship
    classif: relationship
    classif_auto: relationship
    classifier: relationship
    img0: relationship
    all_images: relationship
    sample: relationship
    acquisition: relationship
    process: relationship

    @classmethod
    def fetch_existing_objects(cls, session: Session, prj_id) -> Dict[str, int]:
        ret = {}
        # TODO: Why using the view? Why an outer join in the view?
        res: ResultProxy = session.execute(
            "SELECT o.orig_id, o.objid "
            "  FROM objects o "
            " WHERE o.projid = :prj",
            {"prj": prj_id})
        for rec in res:
            ret[rec[0]] = rec[1]
        return ret

    @staticmethod
    def update_counts_and_img0(session: Session, prj_id):
        # noinspection SqlRedundantOrderingDirection
        session.execute("""
        UPDATE obj_head o
           SET imgcount = (SELECT count(*) FROM images WHERE objid = o.objid),
               img0id = (SELECT imgid FROM images WHERE objid = o.objid ORDER BY imgrank ASC LIMIT 1)
         WHERE projid = :prj
           AND (imgcount IS NULL or img0id IS NULL) """,
                        {'prj': prj_id})
        session.commit()

    @staticmethod
    def _geo_from_txt(txt: str, min_v: float, max_v: float) -> float:
        """ Convert/check latitude or longitude before setting field
            :raises ValueError """
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
        """ Convert depth before setting field
            :raises ValueError """
        return float(txt)

    @staticmethod
    def time_from_txt(txt: str) -> datetime.time:
        """ Convert/check time before setting field. HHMM with optional SS.
            :raises ValueError """
        # Left pad with 0s as they tend to be truncated by spreadsheets e.g. 320 -> 0320
        txt = '0' * (4 - len(txt)) + txt if len(txt) < 4 else txt
        # Right pad with 0s for seconds e.g. 0320 -> 032000
        txt += '0' * (6 - len(txt)) if len(txt) < 6 else ""
        return datetime.time(int(txt[0:2]), int(txt[2:4]), int(txt[4:6]))

    @staticmethod
    def date_from_txt(txt: str) -> datetime.date:
        """ Convert/check date before setting field
            :raises ValueError """
        return datetime.date(int(txt[0:4]), int(txt[4:6]), int(txt[6:8]))


class ObjectFields(Model):
    __tablename__ = 'obj_field'
    objfid = Column(BIGINT, ForeignKey(ObjectHeader.objid, ondelete="CASCADE"), primary_key=True)
    # TODO: Isn't this the natural PK for objects?, it looks unique per projet
    orig_id = Column(VARCHAR(255))
    # TODO: Can't see any value in DB
    object_link = Column(VARCHAR(255))
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship


# Ajout des colonnes numériques & textuelles libres
for i in range(1, 501):
    # 8 bytes each, if present
    setattr(ObjectFields, "n%02d" % i, Column(FLOAT))
for i in range(1, 21):
    setattr(ObjectFields, "t%02d" % i, Column(VARCHAR(250)))


class ObjectCNNFeature(Model):
    __tablename__ = 'obj_cnn_features'
    objcnnid = Column(BIGINT, ForeignKey('obj_head.objid', ondelete="CASCADE"), primary_key=True)
    # The relationships are created in Relations.py but the typing here helps the IDE
    object: relationship



# Ajout des colonnes numériques & textuelles libres
for i in range(1, 51):
    setattr(ObjectCNNFeature, "cnn%02d" % i, Column(REAL))

# Index('IS_ObjectsProject',Object.projid,Object.classif_qual)
# utile pour home de  classif manu, car PG ne sait pas utiliser les Skip scan index.
Index('is_objectsprojectonly', ObjectHeader.projid)
Index('is_objectsprojclassifqual', ObjectHeader.projid, ObjectHeader.classif_id, ObjectHeader.classif_qual)
Index('is_objectssample', ObjectHeader.sampleid)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectslatlong', ObjectHeader.latitude, ObjectHeader.longitude)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectsdepth', ObjectHeader.depth_max, ObjectHeader.depth_min, ObjectHeader.projid)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectstime', ObjectHeader.objtime, ObjectHeader.projid)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectsdate', ObjectHeader.objdate, ObjectHeader.projid)
Index('is_objectsprojrandom', ObjectHeader.projid, ObjectHeader.random_value,
      ObjectHeader.classif_qual)
Index('is_objectfieldsorigid', ObjectFields.orig_id)
# For FK checks during deletion
Index('is_objectsacquisition', ObjectHeader.acquisid)
Index('is_objectsprocess', ObjectHeader.processid)

class ObjectsClassifHisto(Model):
    __tablename__ = 'objectsclassifhisto'
    objid = Column(BIGINT, ForeignKey('obj_head.objid', ondelete="CASCADE"), primary_key=True)
    # TODO: FK on taxonomy
    classif_date = Column(TIMESTAMP, primary_key=True)
    classif_type = Column(CHAR(1))  # A : Automatic, M : Manual
    classif_id = Column(INTEGER)
    classif_qual = Column(CHAR(1))
    classif_who = Column(Integer, ForeignKey('users.id'))
    classif_score = Column(DOUBLE_PRECISION)
