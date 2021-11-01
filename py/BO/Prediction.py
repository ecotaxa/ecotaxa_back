# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A prediction is the output of an automatic classification process.
#    This is heavily based on machine learning algorithms.
#
from typing import Any, List, Dict

import numpy as np  # type: ignore
from numpy import ndarray

from BO.Object import ObjectIDT
from DB import ObjectHeader, Acquisition, Sample, ObjectCNNFeature, CNNFeature, Image
from DB.CNNFeature import ObjectCNNFeaturesBean
from DB.Project import ProjectIDT
from DB.helpers import Session, Result
from DB.helpers.DBWriter import DBWriter
from DB.helpers.ORM import Query, and_
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class DeepFeatures(object):
    """
        ML predicting algorithm takes as input "features" which can be either input into EcoTaxa, and correspond
        to various measurements on the image and arbitrary data. @See ObjectFields.

        OTOH, it can also _generate_ features, using another class of machine learning algorithm: CNN
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

    @staticmethod
    def find_missing(session: Session, proj_id: ProjectIDT) -> Dict[ObjectIDT, str]:
        """
            Find missing cnn features for this project.
        """
        qry: Query = session.query(ObjectHeader.objid, Image.file_name)
        qry = qry.join(Acquisition, Acquisition.acquisid == ObjectHeader.acquisid)
        qry = qry.join(Sample, and_(Sample.sampleid == Acquisition.acq_sample_id,
                                    Sample.projid == proj_id))
        qry = qry.outerjoin(Image)  # For detecting missing images
        qry = qry.outerjoin(ObjectCNNFeature)  # For detecting missing features
        # noinspection PyComparisonWithNone
        qry = qry.filter(ObjectCNNFeature.objcnnid == None)  # SQLAlchemy
        qry = qry.order_by(ObjectHeader.objid, Image.imgrank)
        ret = {}
        for a_res in session.execute(qry):
            objid, img_file = a_res
            assert img_file is not None, "Object %d has no image in DB" % objid
            if not objid in ret:
                ret[objid] = img_file
            else:  # Only pick the first image
                pass
        return ret

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

    @classmethod
    def read_for_objects(cls, session: Session, oid_lst: List[int]) -> Result:  # TODO: Should be ObjectIDListT
        """
            Read CNN lines AKA features, in order, for given object_ids
        """
        fk_to_objid = ObjectCNNFeature.objcnnid.name
        sql = "WITH ordr (seq, objid) AS (select * from UNNEST(:seq, :oids)) "
        sql += "SELECT " + ",".join(CNNFeature.DEEP_FEATURES)
        sql += " FROM " + ObjectCNNFeature.__tablename__
        sql += " JOIN ordr ON " + fk_to_objid + " = ordr.objid "
        sql += " ORDER BY ordr.seq "
        params = {"seq": list(range(len(oid_lst))),
                  "oids": oid_lst}
        res: Result = session.execute(sql, params=params)
        return res

    @classmethod
    def np_read_for_objects(cls, session: Session, oid_lst: List[int]) -> ndarray:
        """
            Read CNN lines AKA features, in order, for given object_ids, into a NumPy array
        """
        res = cls.read_for_objects(session, oid_lst)
        ret = np.ndarray(shape=(len(oid_lst), len(res.keys())), dtype=np.float32)
        ndx = 0
        for a_row in res:
            ret[ndx] = a_row
            ndx += 1
        assert ndx == len(oid_lst), "No enough CNN features in DB: expected %d read %d" % (len(oid_lst), ndx)
        return ret
