import logging

from starlette import status

from tests.credentials import ADMIN_AUTH, REAL_USER_ID, CREATOR_AUTH
from tests.emodnet_ref import ref_zip, with_zeroes_zip, no_computations_zip
from tests.test_classification import _prj_query, OBJECT_SET_CLASSIFY_URL
from tests.test_collections import COLLECTION_UPDATE_URL, COLLECTION_QUERY_URL
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_jobs import wait_for_stable, api_check_job_ok, api_check_job_failed
from tests.test_update_prj import PROJECT_UPDATE_URL

OBJECT_SET_EXPORT_URL = "/object_set/export"


def test_export_tsv(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "TSV export project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "TSV export project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    prj_json = rsp.json()

    caplog.set_level(logging.DEBUG)

    # Admin exports it
    url = OBJECT_SET_EXPORT_URL
    req = {"project_id": prj_id,
           "exp_type": "TSV",
           "tsv_entities": "OPASHC",
           "coma_as_separator": True,
           "with_images": True,
           "only_first_image": True,
           "split_by": "sample",
           "with_internal_ids": False,
           "out_to_ftp": False,
           "sum_subtotal": ""}
    filters = {}
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)

    # Backup export
    req["exp_type"] = "BAK"
    req["with_images"] = True
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
