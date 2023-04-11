# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exhibit some not-so-intuitive behavior of /my_files and associated upload
#

import logging
import shutil

import pytest
from starlette import status

from tests.credentials import ADMIN_USER_ID, CREATOR_AUTH, CREATOR_USER_ID
from tests.test_import import (
    FILE_IMPORT_URL,
    SHARED_DIR,
    PLAIN_DIR,
    PLAIN_FILE,
    V6_FILE,
    create_project,
    PLAIN_FILE_PATH,
)
from tests.test_jobs import (
    wait_for_stable,
    api_wait_for_stable_job,
    api_check_job_ok,
    api_check_job_errors,
)
from tests.test_import_simple import UPLOAD_FILE_URL


@pytest.mark.parametrize("title", ["Try my files"])
def test_my_files(config, database, fastapi, caplog, title):
    """
    Simple import with no fixed values at all, but using the upload directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(CREATOR_USER_ID, title)

    TAG = "XXX"
    DEST_FILE_NAME = "LOKI_46-24hours_01.zip"

    # Copy an existing test file into current dir, simulating client side
    shutil.copyfile(SHARED_DIR / V6_FILE, DEST_FILE_NAME)

    # Upload this file
    with open(DEST_FILE_NAME, "rb") as fin:
        upload_rsp = fastapi.post(
            UPLOAD_FILE_URL,
            headers=CREATOR_AUTH,
            data={"tag": TAG},  # /!\ If no tag -> random use-once directory!
            files={"file": fin},
        )
        assert upload_rsp.status_code == 200
        srv_file_path = upload_rsp.json()
        assert TAG in srv_file_path

    # The tag becomes a top-level directory
    list_rsp = fastapi.get(UPLOAD_FILE_URL, headers=CREATOR_AUTH)
    assert list_rsp.status_code == 200
    my_files_root: Dict = list_rsp.json()
    assert my_files_root["path"] == ""
    assert len(my_files_root["entries"]) == 1
    assert my_files_root["entries"][0] == {
        "mtime": "",
        "name": TAG,
        "size": 0,
        "type": "D",
    }

    # The file is stored in the subdirectory
    list_rsp = fastapi.get(UPLOAD_FILE_URL + TAG, headers=CREATOR_AUTH)
    assert list_rsp.status_code == 200
    my_files_subdir: Dict = list_rsp.json()
    assert my_files_subdir["path"] == TAG
    assert len(my_files_subdir["entries"]) == 1
    the_file = my_files_subdir["entries"][0]
    del the_file["mtime"]  # Unpredictable
    assert the_file == {"name": DEST_FILE_NAME, "size": 22654, "type": "F"}

    # Import the file without the right path -> Error
    url = FILE_IMPORT_URL.format(project_id=prj_id)
    req = {"source_path": DEST_FILE_NAME}
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    api_wait_for_stable_job(fastapi, job_id)
    errors = api_check_job_errors(fastapi, job_id)
    assert "FileNotFoundError" in "".join(errors)

    # Import the file with the right path
    # The below (unfortunately) hard-coded path is valid on current configuration of EcoTaxa
    file_path = "/tmp/ecotaxa_user.{}/{}/{}".format(
        CREATOR_USER_ID,  # Should come from /api/users/me
        TAG,  # existing tag, created the on the first file creation with it
        DEST_FILE_NAME,  # can come from an entry in GET /my_files/TAG
    )
    req = {"source_path": file_path}
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    api_wait_for_stable_job(fastapi, job_id)
    api_check_job_ok(fastapi, job_id)
