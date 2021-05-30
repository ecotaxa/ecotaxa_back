import logging
from io import BytesIO
from zipfile import ZipFile

from starlette import status

from tests.credentials import ADMIN_AUTH, REAL_USER_ID, CREATOR_AUTH
from tests.emodnet_ref import ref_zip, with_zeroes_zip, no_computations_zip
from tests.test_classification import _prj_query, OBJECT_SET_CLASSIFY_URL
from tests.test_collections import COLLECTION_UPDATE_URL, COLLECTION_QUERY_URL
from tests.test_export_emodnet import JOB_DOWNLOAD_URL
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_jobs import wait_for_stable, api_check_job_ok, api_check_job_failed, get_job_and_wait_until_ok
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
           "only_first_image": False,
           "split_by": "sample",
           "with_internal_ids": False,
           "out_to_ftp": False,
           "sum_subtotal": ""}
    filters = {}
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id)

    # Backup export
    req["exp_type"] = "BAK"
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id)

    # DOI export
    req["exp_type"] = "DOI"
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id)

    # TSV export
    req["exp_type"] = "TSV"
    req["with_internal_ids"] = True
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id)


def download_and_unzip_and_check(fastapi, job_id):
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, with_zeroes_zip)


def unzip_and_check(zip_content, ref_content):
    pseudo_file = BytesIO(zip_content)
    zip = ZipFile(pseudo_file)
    for a_file in zip.filelist:
        name = a_file.filename
        with zip.open(name) as myfile:
            content_bin = myfile.read()
