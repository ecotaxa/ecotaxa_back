# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy import Index, Column, ForeignKey, Sequence, Integer
from sqlalchemy.dialects.postgresql import BIGINT, VARCHAR, INTEGER, REAL, DOUBLE_PRECISION, DATE, TIME, FLOAT, CHAR, \
    TIMESTAMP
from sqlalchemy.engine import ResultProxy
from sqlalchemy.orm import relationship, Session

from .Model import Model
# noinspection PyUnresolvedReferences
from .Taxonomy import Taxonomy
# noinspection PyUnresolvedReferences
from .User import User

# Classification qualification
classif_qual = {'P': 'predicted', 'D': 'dubious', 'V': 'validated'}
classif_qual_revert = {}
for (k, v) in classif_qual.items():
    classif_qual_revert[v] = k


def GetClassifQualClass(q):
    if q in classif_qual:
        return 'status-' + classif_qual[q]
    return 'status-unknown'


# TODO: SQLAlchemy uses nextval(seq) in the generated SQL
#  It's probably possible that the seq is used server-side and not needed in client SQL
#   Python side: Sequence('seq_objects', optional=True)
#   Server-side: SERIAL/IDENTITY/Trigger?
class Object(Model):
    __tablename__ = 'obj_head'
    objid = Column(BIGINT, Sequence('seq_objects'), primary_key=True)

    projid = Column(INTEGER, ForeignKey('projects.projid'), nullable=False)

    project = relationship("Project")
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
    classif = relationship("Taxonomy", primaryjoin="Taxonomy.id==Object.classif_id", foreign_keys="Taxonomy.id",
                           uselist=False, )
    classif_qual = Column(CHAR(1))
    classif_who = Column(Integer, ForeignKey('users.id'))
    classiffier = relationship("User", primaryjoin="User.id==Object.classif_who", foreign_keys="User.id",
                               uselist=False, )
    classif_when = Column(TIMESTAMP)

    classif_auto_id = Column(INTEGER)
    classif_auto_score = Column(DOUBLE_PRECISION)
    classif_auto_when = Column(TIMESTAMP)
    classif_auto = relationship("Taxonomy", primaryjoin="Taxonomy.id==foreign(Object.classif_auto_id)", uselist=False, )

    classif_crossvalidation_id = Column(INTEGER)
    #
    # The _first_ image
    # Relation b/w next images and present Object are in Image.objid
    # TODO: WTF, normalize.
    img0id = Column(BIGINT)
    img0 = relationship("Image", foreign_keys="Image.objid")
    imgcount = Column(INTEGER)
    images = relationship("Image")
    complement_info = Column(VARCHAR)

    similarity = Column(DOUBLE_PRECISION)

    # TODO: Why random? It makes testing a bit more difficult
    random_value = Column(INTEGER)

    sampleid = Column(INTEGER, ForeignKey('samples.sampleid'))
    sample = relationship("Sample")
    acquisid = Column(INTEGER, ForeignKey('acquisitions.acquisid'))
    acquis = relationship("Acquisition")
    processid = Column(INTEGER, ForeignKey('process.processid'))
    processrel = relationship("Process")
    objfrel = relationship("ObjectFields", uselist=False, back_populates="objhrel")

    @classmethod
    def fetch_existing_objects(cls, session: Session, prj_id):
        ret = set()
        # TODO: Why using the view? Why an outer join in the view?
        res: ResultProxy = session.execute(
            "SELECT o.orig_id "
            "  FROM objects o "
            " WHERE o.projid = :prj",
            {"prj": prj_id})
        for rec in res:
            ret.add(rec[0])
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


class ObjectFields(Model):
    __tablename__ = 'obj_field'
    objfid = Column(BIGINT, ForeignKey(Object.objid, ondelete="CASCADE"), primary_key=True)
    objhrel = relationship("Object", uselist=False, back_populates="objfrel")
    # TODO: Isn't this the natural PK for objects?, it looks unique per projet
    orig_id = Column(VARCHAR(255))
    # TODO: Can't see any value in DB
    object_link = Column(VARCHAR(255))


# Ajout des colonnes numériques & textuelles libres
for i in range(1, 501):
    # 8 bytes each, if present
    setattr(ObjectFields, "n%02d" % i, Column(FLOAT))
for i in range(1, 21):
    setattr(ObjectFields, "t%02d" % i, Column(VARCHAR(250)))


class ObjectCNNFeature(Model):
    __tablename__ = 'obj_cnn_features'
    objcnnid = Column(BIGINT, ForeignKey('obj_head.objid', ondelete="CASCADE"), primary_key=True)
    objhrel = relationship("Object", foreign_keys="Object.objid",
                           primaryjoin="ObjectCNNFeature.objcnnid==Object.objid", uselist=False,
                           backref="objcnnrel")


# Ajout des colonnes numériques & textuelles libres
for i in range(1, 51):
    setattr(ObjectCNNFeature, "cnn%02d" % i, Column(REAL))

# Index('IS_ObjectsProject',Object.projid,Object.classif_qual)
# utile pour home de  classif manu, car PG ne sait pas utiliser les Skip scan index.
Index('is_objectsprojectonly', Object.projid)
Index('is_objectsprojclassifqual', Object.projid, Object.classif_id, Object.classif_qual)
Index('is_objectssample', Object.sampleid)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectslatlong', Object.latitude, Object.longitude)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectsdepth', Object.depth_max, Object.depth_min, Object.projid)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectstime', Object.objtime, Object.projid)
# TODO: This is sample attributes, indexing here is waste
Index('is_objectsdate', Object.objdate, Object.projid)
Index('is_objectsprojrandom', Object.projid, Object.random_value,
      Object.classif_qual)
Index('is_objectfieldsorigid', ObjectFields.orig_id)


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
