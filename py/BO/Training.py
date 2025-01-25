# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, NamedTuple

from sqlalchemy import tuple_

from BO.Classification import (
    HistoricalLastClassif,
    ClassifIDT,
    ClassifIDListT,
    ClassifScoresListT,
)
from BO.User import UserIDT
from DB import Session
from DB.Object import (
    ObjectIDT,
    ObjectHeader,
    ObjectsClassifHisto,
    PREDICTED_CLASSIF_QUAL,
    ObjectIDListT,
)
from DB.Prediction import (
    Prediction,
    PredictionHisto,
    ClassifScore,
)
from DB.Training import Training, TrainingIDT
from DB.helpers.Core import select
from DB.helpers.ORM import Delete, any_, and_
from helpers import DateTime
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


# Present prediction
class PredictionInfoT(NamedTuple):
    object_id: ObjectIDT
    classif_id: ClassifIDT
    score: float


class TrainingBO(object):
    """
    A training, i.e. the event of producing predictions for lots of objects.
    """

    __slots__ = [
        "_training",
    ]

    def __init__(self, training: Training):
        self._training = training

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a training field somehow then return it"""
        return getattr(self._training, item)

    @property
    def training(self) -> Training:
        return self._training

    def advance(self):
        """Mark some progress by updating training_end"""
        self._training.training_end = DateTime.now_time()

    @classmethod
    def create_one(
        cls,
        session: Session,
        author: UserIDT,
        reason: str,
        training_start: Optional[datetime] = None,
    ) -> "TrainingBO":
        trn = Training()
        trn.training_start = (
            DateTime.now_time() if training_start is None else training_start
        )
        trn.training_end = datetime.fromtimestamp(0)  # In progress
        trn.training_author = author
        trn.training_path = reason
        session.add(trn)
        session.flush([trn])  # to get the training ID populated
        logger.info("create_one: %s", str(trn))
        return TrainingBO(trn)

    @classmethod
    def find_by_start_time_or_create(
        cls, session: Session, author: UserIDT, reason: str, start_time: datetime
    ) -> "TrainingBO":
        ret = (
            session.query(Training)
            .filter(Training.training_start == start_time)
            .first()
        )
        if ret is None:
            return cls.create_one(session, author, reason, start_time)
        else:
            return TrainingBO(ret)


class TrainingBOProvider(object):
    """We don't want to create empty trainings, so provide one only when we know it will be useful,
    i.e. filled with predictions."""

    def __init__(
        self,
        session: Session,
        user_id: UserIDT,
        reason: str,
        training_start: Optional[datetime] = None,
    ):
        self.session: Session = session
        self.user_id = user_id
        self.training_start = (
            DateTime.now_time() if training_start is None else training_start
        )
        self.path = reason
        self.current_training: Optional[TrainingBO] = None

    def provide(self) -> TrainingBO:
        if self.current_training is None:
            self.current_training = TrainingBO.find_by_start_time_or_create(
                self.session,
                self.user_id,
                self.path,
                self.training_start,
            )
        return self.current_training


class PredictionBO(object):
    """
    Work on predictions & historical ones.
    """

    def __init__(self, session: Session, object_ids: ObjectIDListT):
        self.session = session
        assert isinstance(object_ids, list)
        assert len(object_ids) == 0 or isinstance(object_ids[0], ObjectIDT)
        self.object_ids = object_ids

    def get_prediction_infos(self) -> List[PredictionInfoT]:
        """
        Return the predictions, per object in decreasing score.
        """
        qry = select(Prediction.object_id, Prediction.classif_id, Prediction.score)
        qry = qry.join(ObjectHeader)
        qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
        qry = qry.order_by(Prediction.object_id, Prediction.score.desc())
        with CodeTimer("Preds for %d objs: " % len(self.object_ids), logger):
            return [
                PredictionInfoT(objid, classif_id, score)
                for (objid, classif_id, score) in self.session.execute(qry)
            ]

    MAX_PREDICTIONS_PER_OBJECT = 3  # How many (classif_id, score) we keep per object

    def store_predictions(
        self,
        training_id: TrainingIDT,
        classif_id_lists: List[ClassifIDListT],
        classif_score_lists: List[ClassifScoresListT],
    ) -> Dict[ClassifIDT, List[ClassifScore]]:
        # Bulk insert into the Predictions table, of max_preds (classif_id, score) per object
        max_preds = self.MAX_PREDICTIONS_PER_OBJECT
        preds_for_bulk = []
        preds_by_object: Dict[ObjectIDT, List[ClassifScore]] = {}
        for obj_id, list_classifs, list_scores in zip(
            self.object_ids, classif_id_lists, classif_score_lists
        ):
            preds_for_object = [
                ClassifScore(classif, score)
                for classif, score in zip(
                    list_classifs[:max_preds], list_scores[:max_preds]
                )
            ]
            preds_by_object[obj_id] = preds_for_object
            for pred_classif, pred_score in preds_for_object:
                preds_for_bulk.append(
                    {
                        Prediction.training_id.name: training_id,
                        Prediction.object_id.name: obj_id,
                        Prediction.classif_id.name: pred_classif,
                        Prediction.score.name: pred_score,
                    }
                )
        self.session.bulk_insert_mappings(Prediction, preds_for_bulk)
        return preds_by_object

    def historize_predictions(self) -> PredictionBO:
        """
        Historize by moving Prediction rows to PredictionHisto table
        Note: A prediction can be _partly_ historized, i.e. some objects are in history but not some others.
        """
        here_sel = select(
            Prediction.training_id,
            Prediction.object_id,
            Prediction.classif_id,
            Prediction.score,
        ).where(Prediction.object_id == any_(self.object_ids))
        histo_qry = PredictionHisto.__table__.insert().from_select(
            [
                Prediction.training_id.name,
                Prediction.object_id.name,
                Prediction.classif_id.name,
                Prediction.score.name,
            ],
            here_sel,
        )
        self.session.execute(histo_qry)
        self._remove_current_predictions()
        return self

    def _remove_current_predictions(self) -> PredictionBO:
        del_qry: Delete = Prediction.__table__.delete()
        del_qry = del_qry.where(Prediction.object_id == any_(self.object_ids))
        self.session.execute(del_qry)
        return self

    def resurrect_predictions(self, histo: List[HistoricalLastClassif]):
        """
        A set of objects are going to become again predicted from an historical training, effectively inverting
        above historisation.
        """
        self._remove_current_predictions()
        pred_histos = [
            (an_histo.objid, an_histo.histo_classif_date, an_histo.histo_classif_id)
            for an_histo in histo
            if an_histo.histo_classif_qual == PREDICTED_CLASSIF_QUAL
        ]
        # Determine historized PredictionHisto rows to resurrect. A bit tricky as all we have is dates.
        histo_sel = select(
            PredictionHisto.training_id,
            PredictionHisto.object_id,
            PredictionHisto.classif_id,
            PredictionHisto.score,
        )
        histo_sel = histo_sel.join(
            Training, Training.training_id == PredictionHisto.training_id
        )
        histo_sel = histo_sel.join(
            ObjectsClassifHisto,
            and_(  # We start from a single line per obj and eventually end up in several, with all possible scores
                ObjectsClassifHisto.objid == PredictionHisto.object_id,
                ObjectsClassifHisto.classif_date.between(
                    Training.training_start, Training.training_end
                ),
            ),
        )
        histo_sel = histo_sel.where(
            tuple_(  # type:ignore
                ObjectsClassifHisto.objid,
                ObjectsClassifHisto.classif_date,
                ObjectsClassifHisto.classif_id,
            ).in_(pred_histos)
        )
        # Insert historized PredictionHisto into Prediction
        resurrect_qry = Prediction.__table__.insert().from_select(
            [
                PredictionHisto.training_id.name,
                PredictionHisto.object_id.name,
                PredictionHisto.classif_id.name,
                PredictionHisto.score.name,
            ],
            histo_sel,
        )
        self.session.execute(resurrect_qry)
        # Remove history which is now current
        histo_pred_del_qry: Delete = PredictionHisto.__table__.delete()
        histo_pred_del_qry = histo_pred_del_qry.where(
            tuple_(  # type:ignore
                PredictionHisto.training_id,
                PredictionHisto.object_id,
                PredictionHisto.classif_id,
                PredictionHisto.score,
            ).in_(histo_sel)
        )
        self.session.execute(histo_pred_del_qry)
