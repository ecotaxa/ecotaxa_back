# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


import logging

import pytest

# noinspection PyPackageRequirements
from API_models.imports import *

# Import services
# noinspection PyPackageRequirements
# noinspection PyPackageRequirements
from API_operations.imports.SimpleImport import SimpleImport

# # noinspection PyUnresolvedReferences
# from tests.config_fixture import config
# # noinspection PyUnresolvedReferences
# from tests.db_fixture import database
from starlette import status

from tests.credentials import ADMIN_USER_ID, CREATOR_AUTH, CREATOR_USER_ID
from tests.test_import import PLAIN_DIR, create_project, PLAIN_FILE_PATH
from tests.jobs import check_job_ok
from tests.api_wrappers import api_wait_for_stable_job, MY_FILES_URL

IMPORT_IMAGES_URL = "/simple_import/{project_id}?dry_run={dry_run}"


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Test Import Images"])
def test_import_images_only(fastapi, caplog, title):
    """
    Simple import AKA image only import, with fixed values.
    """
    do_import_images_via_service(fastapi, caplog, title)


def do_import_images_via_service(fastapi, caplog, title):
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, title)

    vals: Dict[SimpleImportFields, str] = {
        SimpleImportFields.latitude: "abcde",
        SimpleImportFields.longitude: "456.5",
        SimpleImportFields.depthmin: "very very low",
    }
    params = SimpleImportReq(task_id=0, source_path=str(PLAIN_DIR), values=vals)
    with SimpleImport(prj_id, params, dry_run=True) as sce:
        rsp = sce.run(ADMIN_USER_ID)
    assert rsp.errors == [
        "'abcde' is not a valid value for latitude",
        "'456.5' is not a valid value for longitude",
        "'very very low' is not a valid value for depthmin",
    ]
    vals[SimpleImportFields.latitude] = "43.8802"
    vals[SimpleImportFields.longitude] = "7.2329"
    vals[SimpleImportFields.depthmin] = "500"
    # check classif params
    vals[SimpleImportFields.status] = "V"
    params = SimpleImportReq(task_id=0, source_path=str(PLAIN_DIR), values=vals)
    with SimpleImport(prj_id, params, dry_run=True) as sce:
        rsp = sce.run(ADMIN_USER_ID)
    assert rsp.errors == [
        "'None' is not a valid value for taxolb as at least one annotation value is set.",
        "'None' is not a valid value for userlb as at least one annotation value is set.",
        "'None' is not a valid value for datelb as at least one annotation value is set.",
    ]
    vals[SimpleImportFields.userlb] = "2"
    params = SimpleImportReq(task_id=0, source_path=str(PLAIN_DIR), values=vals)
    with SimpleImport(prj_id, params, dry_run=True) as sce:
        rsp = sce.run(ADMIN_USER_ID)
    assert rsp.errors == [
        "'None' is not a valid value for taxolb as at least one annotation value is set.",
        "'None' is not a valid value for datelb as at least one annotation value is set.",
    ]
    vals[SimpleImportFields.taxolb] = "12"
    params = SimpleImportReq(task_id=0, source_path=str(PLAIN_DIR), values=vals)
    with SimpleImport(prj_id, params, dry_run=True) as sce:
        rsp = sce.run(ADMIN_USER_ID)
    assert rsp.errors == [
        "'None' is not a valid value for datelb as at least one annotation value is set."
    ]
    # Do real import
    vals[SimpleImportFields.datelb] = "20240706"
    params.values = vals
    with SimpleImport(prj_id, params, dry_run=False) as sce:
        rsp: SimpleImportRsp = sce.run(ADMIN_USER_ID)
    assert rsp.errors == []
    job_id = rsp.job_id
    job = api_wait_for_stable_job(fastapi, job_id)
    check_job_ok(job)
    assert job.result["nb_images"] == 8
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()

    # Second run, ensure we don't create dummy parents
    caplog.clear()
    with SimpleImport(prj_id, params, dry_run=False) as sce:
        rsp: SimpleImportRsp = sce.run(ADMIN_USER_ID)
    job_id2 = rsp.job_id
    assert job_id2 > job_id
    _ = api_wait_for_stable_job(fastapi, job_id2)
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
        assert "++ ID" not in a_msg.getMessage()

    return prj_id


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Simple via fastapi"])
def test_api_simple_import_images(fastapi, title):
    """
    Simple import with no fixed values at all, but using the upload directory.
    """
    do_simple_import_images(fastapi, title)


def do_simple_import_images(fastapi, title):
    prj_id = create_project(CREATOR_USER_ID, title)
    with open(PLAIN_FILE_PATH, "rb") as fin:
        upload_rsp = fastapi.post(
            MY_FILES_URL,
            headers=CREATOR_AUTH,
            files={"file": fin},
        )
        assert upload_rsp.status_code == 200
        srv_file_path = upload_rsp.json()

    url = IMPORT_IMAGES_URL.format(project_id=prj_id, dry_run=False)
    srv_file_path = srv_file_path.replace(".zip", "")  # New MyFile unzips automatically
    req = {"source_path": srv_file_path, "values": {}}
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    assert job_id > 0
    job = api_wait_for_stable_job(fastapi, job_id)
    check_job_ok(job)
    return prj_id
