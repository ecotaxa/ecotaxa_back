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
from tests.test_import import PLAIN_DIR, PLAIN_FILE, create_project, PLAIN_FILE_PATH
from tests.test_jobs import wait_for_stable, api_wait_for_stable_job

IMPORT_IMAGES_URL = "/simple_import/{project_id}?dry_run={dry_run}"
UPLOAD_FILE_URL = "/my_files/"


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Test Import Images"])
def test_import_images_only(config, database, caplog, title):
    """
        Simple import AKA image only import, with fixed values.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, title)

    vals = {"latitude": "abcde",
            "longitude": "456.5",
            "depthmin": "very very low"}
    params = SimpleImportReq(task_id=0,
                             source_path=str(PLAIN_DIR),
                             values=vals)
    with SimpleImport(prj_id, params, dry_run=True) as sce:
        rsp = sce.run(ADMIN_USER_ID)
    assert rsp.errors == ["'abcde' is not a valid value for SimpleImportFields.latitude",
                          "'456.5' is not a valid value for SimpleImportFields.longitude",
                          "'very very low' is not a valid value for SimpleImportFields.depthmin"]
    # Do real import
    vals["latitude"] = "43.8802"
    vals["longitude"] = "7.2329"
    vals["depthmin"] = "500"
    params.values = vals
    with SimpleImport(prj_id, params, dry_run=False) as sce:
        rsp: SimpleImportRsp = sce.run(ADMIN_USER_ID)
    print("\n".join(caplog.messages))
    assert rsp.errors == []
    job_id = rsp.job_id
    job = wait_for_stable(job_id)
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
    job = wait_for_stable(job_id2)
    print("\n2:".join(caplog.messages))
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
        assert "++ ID" not in a_msg.getMessage()

    return prj_id


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Simple via fastapi"])
def test_api_import_images(config, database, fastapi, caplog, title):
    """
        Simple import with no fixed values at all, but using the upload directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(CREATOR_USER_ID, title)

    with open(PLAIN_FILE_PATH, "rb") as fin:
        upload_rsp = fastapi.post(UPLOAD_FILE_URL, headers=CREATOR_AUTH, files={"file": fin})
        assert upload_rsp.status_code == 200
        srv_file_path = upload_rsp.json()

    url = IMPORT_IMAGES_URL.format(project_id=prj_id, dry_run=False)
    req = {"source_path": srv_file_path,
           "values": {}}
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    assert job_id > 0
    job = api_wait_for_stable_job(fastapi, job_id)
    return prj_id
