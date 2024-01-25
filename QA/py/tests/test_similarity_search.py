import logging
import pytest
import pandas as pd
import numpy as np

from starlette import status

from tests.credentials import ADMIN_AUTH
from tests.jobs import get_job_and_wait_until_ok, api_check_job_ok
from tests.test_objectset_query import _prj_query

from BO.Prediction import DeepFeatures

from API_operations.CRUD.ObjectParents import SamplesService

OBJECT_SET_SIMILARITY_SEARCH_URL = "/object_set/similarity_search"


def test_similarity_search(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import

    prj_id = test_import(database, caplog, "Test Similarity Search")

    obj_ids = _prj_query(fastapi, ADMIN_AUTH, prj_id)
    assert len(obj_ids) == 8
    
    # Test similarity search without features
    url = OBJECT_SET_SIMILARITY_SEARCH_URL
    req = {
        "project_id": prj_id,
        "target_id": obj_ids[0],
    }
    filters = {}
    req_and_filters = {"filters": filters, "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)

    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["neighbor_ids"] == []
    assert rsp.json()["message"] == "Missing CNN features, feature extraction job launched"

    # Insert dummy features
    features = list()
    for i, oi in enumerate(obj_ids):
        features.append([(i + 1) * 0.1] * 50)
    features_df = pd.DataFrame(features, index=obj_ids)

    with SamplesService() as sce:
        n_inserts = DeepFeatures.save(sce.session, features_df)
        assert n_inserts == 8
        sce.session.commit()

    # Test similarity search with features
    url = OBJECT_SET_SIMILARITY_SEARCH_URL
    req = {
        "project_id": prj_id,
        "target_id": obj_ids[0],
    }
    filters = {}
    req_and_filters = {"filters": filters, "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)

    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["neighbor_ids"] == obj_ids
    assert rsp.json()["message"] == "Success"
