import logging

from starlette import status

from tests.credentials import ADMIN_AUTH
from tests.test_jobs import get_job_and_wait_until_ok

OBJECT_SET_PREDICT_URL = "/object_set/predict"

# noinspection PyUnresolvedReferences
#from API_operations.GPU_Prediction import GPUPredictForProject

def no_test_basic_prediction(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "TSV export project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "TSV export project")

    caplog.set_level(logging.DEBUG)

    # Admin predicts
    url = OBJECT_SET_PREDICT_URL
    req = {"project_id": prj_id,
           "source_project_ids": [prj_id],
           "learning_limit": 10,
           "features": ["fre.area"],
           "categories": [1, 2],
           "use_scn": True,
           "pre_mapping": {}}
    filters = {}
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
