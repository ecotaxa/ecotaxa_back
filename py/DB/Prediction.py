from __future__ import annotations

from DB.helpers.ORM import Model
from DB.helpers.DDL import Column, Sequence, ForeignKey
from DB.helpers.Postgres import BIGINT, INTEGER, DOUBLE_PRECISION, BOOLEAN


class Prediction(Model):
    __tablename__ = 'predictions'

    pred_id = Column(BIGINT, Sequence('seq_predictions'), primary_key=True)
    objid = Column(BIGINT, ForeignKey('obj_head.objid', ondelete="CASCADE"))
    classif_id = Column(INTEGER)
    score = Column(DOUBLE_PRECISION)
    discarded = Column(BOOLEAN)
    