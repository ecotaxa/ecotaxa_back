import datetime
import logging
from unittest import mock

# noinspection PyPackageRequirements
from starlette import status

from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID
from tests.export_shared import download_and_unzip_and_check, download_and_check
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import create_project, do_import, DATA_DIR, dump_project
from tests.test_jobs import get_job_and_wait_until_ok, wait_for_stable, api_check_job_ok, JOB_QUERY_URL

OBJECT_SET_EXPORT_URL = "/object_set/export"

_req_tmpl = {
    "exp_type": "TSV",
    "tsv_entities": "OPASHC",
    "coma_as_separator": False,
    "format_dates_times": False,
    "with_images": False,
    "only_first_image": False,
    "split_by": "sample",
    "with_internal_ids": False,
    "out_to_ftp": False,
    "sum_subtotal": ""}


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
    _prj_json = rsp.json()

    caplog.set_level(logging.DEBUG)

    # Admin exports it
    url = OBJECT_SET_EXPORT_URL
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id})
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "tsv_all_entities_no_img_no_ids")

    # Backup export
    req.update({"exp_type": "BAK",
                "with_images": True,
                "only_first_image": False})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_all_images")

    # Backup export without images (but their ref is still in the TSVs)
    req.update({"exp_type": "BAK",
                "with_images": False,
                "only_first_image": False})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_no_image")

    # DOI export
    req.update({"exp_type": "DOI"})
    fixed_date = datetime.datetime(2021, 5, 30, 11, 22, 33)
    with mock.patch('helpers.DateTime._now_time',
                    return_value=fixed_date):
        rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
        assert rsp.status_code == status.HTTP_200_OK
        _job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # The object_id inside prevents predictability
    # TODO: Better comparison ignoring columns, inject project id and so on
    # download_and_unzip_and_check(fastapi, job_id, "doi", only_hdr=True)

    # TSV export with IDs
    req.update({"exp_type": "TSV",
                "with_internal_ids": True,
                "out_to_ftp": True,
                "coma_as_separator": True})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # Too much randomness inside: IDs, random value
    # TODO: Better comparison ignoring columns
    download_and_unzip_and_check(fastapi, job_id, "tsv_with_ids", only_hdr=True)

    # Summary export, 3 types
    req.update({"exp_type": "SUM",
                "out_to_ftp": True,
                "sum_subtotal": "S"
                })
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_sample", only_hdr=True)

    req.update({"exp_type": "SUM",
                "out_to_ftp": True,
                "sum_subtotal": "A"
                })
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_subsample", only_hdr=True)

    req.update({"exp_type": "SUM",
                "out_to_ftp": True,
                "sum_subtotal": ""
                })
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_whole", only_hdr=True)


def test_export_roundtrip(config, database, fastapi, caplog):
    """ roundtrip export/import/compare"""
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import_uvp6
    prj_id = test_import_uvp6(config, database, caplog, "TSV UVP6 roundtrip export source project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    _prj_json = rsp.json()

    # Admin exports it
    url = OBJECT_SET_EXPORT_URL
    req = {"project_id": prj_id,
           "exp_type": "BAK",
           "tsv_entities": "OPASHC",
           "coma_as_separator": False,
           "format_dates_times": True,
           "with_images": True,
           "only_first_image": False,
           "split_by": "sample",
           "with_internal_ids": False,
           "out_to_ftp": True,
           "sum_subtotal": ""}
    filters = {}
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    file_in_ftp = job_dict["result"]["out_file"]

    # Create a clone project
    clone_prj_id = create_project(ADMIN_USER_ID, "TSV UVP6 roundtrip export clone project")
    do_import(clone_prj_id,
              source_path=DATA_DIR / "ftp" / ("task_%d_%s" % (job_id, file_in_ftp)), user_id=ADMIN_USER_ID)

    # TODO: Automate diff
    with open('exp_source.json', "w") as fd:
        dump_project(ADMIN_USER_ID, prj_id, fd)
    with open('exp_clone.json', "w") as fd:
        dump_project(ADMIN_USER_ID, clone_prj_id, fd)
