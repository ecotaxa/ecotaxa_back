import logging
import pytest
import pandas as pd
import numpy as np

from starlette import status

from tests.credentials import ADMIN_AUTH, CREATOR_AUTH
from tests.jobs import get_job_and_wait_until_ok
from tests.test_classification import query_all_objects

from BO.Prediction import DeepFeatures

from API_operations.CRUD.ObjectParents import SamplesService

from tests.test_import import do_test_import

OBJECT_SET_PREDICT_URL = "/object_set/predict"


# noinspection PyUnresolvedReferences
# from API_operations.GPU_Prediction import GPUPredictForProject


def no_test_basic_prediction(fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    prj_id = do_test_import(fastapi, "TSV export project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(database, caplog, "TSV export project")

    caplog.set_level(logging.DEBUG)

    # Admin predicts
    url = OBJECT_SET_PREDICT_URL
    req = {
        "project_id": prj_id,
        "source_project_ids": [prj_id],
        "learning_limit": 10,
        "features": ["fre.area"],
        "categories": [1, 2],
        "use_scn": True,
        "pre_mapping": {},
    }
    filters = {}
    req_and_filters = {"filters": filters, "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)


def test_prediction_functions(fastapi):

    prj_id = do_test_import(fastapi, "Test Prediction")

    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 8

    # Prepare fake CNN features to insert
    features = list()
    for i, oi in enumerate(obj_ids):
        features.append([(i + 1) * 0.1] * 50)
    features_df = pd.DataFrame(features, index=obj_ids)

    # Test features insertion
    with SamplesService() as sce:
        n_inserts = DeepFeatures.save(sce.session, features_df)
        assert n_inserts == 8
        sce.session.commit()

    # Test features retrieval
    with SamplesService() as sce:
        ret = DeepFeatures.np_read_for_objects(sce.session, obj_ids)
        assert (ret == np.array(features, dtype="float32")).all()

    # Test find_missing without any missing features
    with SamplesService() as sce:
        ret = DeepFeatures.find_missing(sce.session, prj_id)
        assert ret == {}

    # Test deletion
    with SamplesService() as sce:
        n_deletes = DeepFeatures.delete_all(sce.session, prj_id)
        assert n_deletes == 8
        sce.session.commit()

    # Test find_missing after deletion
    with SamplesService() as sce:
        ret = DeepFeatures.find_missing(sce.session, prj_id)
        assert len(ret) == 8

    # Test features retrieval in empty table, should raise an error
    with SamplesService() as sce:
        with pytest.raises(AssertionError):
            ret = DeepFeatures.np_read_for_objects(sce.session, obj_ids)
