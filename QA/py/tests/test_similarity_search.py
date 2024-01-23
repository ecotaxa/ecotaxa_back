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

    # Prepare fake CNN features to insert
    features = list()
    for i, oi in enumerate(obj_ids):
        features.append([(i + 1) * 0.1] * 50)
    features_df = pd.DataFrame(features, index=obj_ids)

    # Insert features
    with SamplesService() as sce:
        n_inserts = DeepFeatures.save(sce.session, features_df)
        assert n_inserts == 8
        sce.session.commit()

    # Test similarity search
    url = OBJECT_SET_SIMILARITY_SEARCH_URL
    req = {
        "project_id": prj_id,
        "target_id": obj_ids[0],
    }
    filters = {}
    req_and_filters = {"filters": filters, "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    assert job_id is not None

    # Check results
    job_dict = api_check_job_ok(fastapi, job_id)
    assert job_dict["result"]["neighbor_ids"] == obj_ids
