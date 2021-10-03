# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A prediction is the output of an automatic classification process.
#    This is heavily based on machine learning algorithms.
#
from typing import Any

from DB import ObjectHeader, Acquisition, Sample, ObjectCNNFeature
from DB.CNNFeature import ObjectCNNFeaturesBean
from DB.Project import ProjectIDT
from DB.helpers import Session
from DB.helpers.DBWriter import DBWriter
from DB.helpers.ORM import Query, and_
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class AutomatedFeatures(object):
    """
        ML predicting algorithm takes as input "features" which can be either input into EcoTaxa, and correspond
        to various measurements on the image and arbitrary data. @See ObjectFields.

        OTOH, it can also generate features, using another class of machine learning algorithm: CNN
         @see https://en.wikipedia.org/wiki/Convolutional_neural_network
        These other features are stored in a dedicated DB table @see ObjectCNNFeature.
    """
    SAVE_EVERY = 500

    @staticmethod
    def delete_all(session: Session, proj_id: ProjectIDT) -> int:
        """
            Delete all CNN features from DB, for this project.
        """
        sub_qry: Query = session.query(ObjectHeader.objid)
        sub_qry = sub_qry.join(Acquisition, Acquisition.acquisid == ObjectHeader.acquisid)
        sub_qry = sub_qry.join(Sample, and_(Sample.sampleid == Acquisition.acq_sample_id,
                                            Sample.projid == proj_id))
        qry: Query = session.query(ObjectCNNFeature)
        qry = qry.filter(ObjectCNNFeature.objcnnid.in_(sub_qry))
        nb_deleted = qry.delete(synchronize_session=False)
        return nb_deleted

    @classmethod
    def save(cls, session: Session, features: Any) -> int:
        """
            Insert CNN features to DB.
            Features is an iterable dict-like, a pandas dataframe for the moment.
        """
        writer = DBWriter(session)
        writer.generators({})  # TODO: A bit weird, DBWriter should be usable straight away
        nb_rows = 0
        # for a_rec in features.to_records(index=True): # This is nice and can produce tuple()
        # but I found no way to feed them into DBWriter without going low-level.
        for obj_id, row in features.iterrows():
            bean = ObjectCNNFeaturesBean(obj_id, row)
            writer.add_cnn_features_with_pk(bean)
            nb_rows += 1
            if nb_rows % cls.SAVE_EVERY == 0:
                writer.do_bulk_save()
        writer.do_bulk_save()
        return nb_rows
