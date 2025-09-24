# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exhibit some not-so-intuitive behavior of /my_files and associated upload
#

import logging
import shutil
from typing import Dict

import pytest
from starlette import status

from tests.credentials import CREATOR_AUTH, CREATOR_USER_ID
from tests.jobs import (
    api_wait_for_stable_job,
    api_check_job_ok,
    api_check_job_errors,
)
from tests.test_import import (
    SHARED_DIR,
    V6_FILE,
    create_project,
    FILE_IMPORT_URL,
)
from tests.test_import_simple import UPLOAD_FILE_URL

SEPARATOR = "/"
DIRPATH = "XXX"


@pytest.mark.parametrize("title", ["Try my files"])
def test_my_files(fastapi, caplog, tstlogs, title):
    """
    Simple import with no fixed values at all, but using the upload directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(CREATOR_USER_ID, title)

    DEST_FILE_NAME = "LOKI_46-24hours_01.zip"
    # Copy an existing test file into current dir, simulating client side
    shutil.copyfile(SHARED_DIR / V6_FILE, tstlogs / DEST_FILE_NAME)
    # Upload this file
    upload_file(fastapi, DEST_FILE_NAME, DIRPATH + "/" + DEST_FILE_NAME, tstlogs)

    # And another
    DEST_FILE_NAME2 = "readme.txt"
    # Copy an existing test file into current dir, simulating client side
    shutil.copyfile(SHARED_DIR / "HOWTO.txt", tstlogs / DEST_FILE_NAME2)
    # Upload this file
    upload_file(fastapi, DEST_FILE_NAME2, DIRPATH + "/" + DEST_FILE_NAME2, tstlogs)

    # The pathparam becomes a top-level directory
    list_rsp = fastapi.get(UPLOAD_FILE_URL + SEPARATOR, headers=CREATOR_AUTH)
    assert list_rsp.status_code == 200
    my_files_root: Dict = list_rsp.json()
    assert my_files_root["path"] == ""
    assert len(my_files_root["entries"]) == 2
    assert my_files_root["entries"][0] == {
        "mtime": "",
        "name": DIRPATH,
        "size": 0,
        "type": "D",
    }

    # The files are stored in the subdirectory
    list_rsp = fastapi.get(UPLOAD_FILE_URL + SEPARATOR + DIRPATH, headers=CREATOR_AUTH)
    assert list_rsp.status_code == 200
    my_files_subdir: Dict = list_rsp.json()
    assert my_files_subdir["path"] == DIRPATH
    assert (
        len(my_files_subdir["entries"]) == 1
    )  # The second file being .txt will have 0 size on re-read
    the_file = [fil for fil in my_files_subdir["entries"] if fil["size"] == 22654][0]
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
        DIRPATH,  # existing tag, created the on the first file creation with it
        DEST_FILE_NAME,  # can come from an entry in GET /my_files/DIRPATH
    )
    req = {"source_path": file_path}
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    api_wait_for_stable_job(fastapi, job_id)
    api_check_job_ok(fastapi, job_id)


def upload_file(fastapi, dest_file_name, pathparam, tstlogs):
    print("uploadfile----------" + str(dest_file_name), pathparam)
    with open(tstlogs / dest_file_name, "rb") as fin:
        upload_rsp = fastapi.post(
            UPLOAD_FILE_URL,
            headers=CREATOR_AUTH,
            data={
                "path": pathparam
            },  # /!\ If no pathparam error-> random use-once directory!
            files={"file": fin},
        )
        assert upload_rsp.status_code == 200
        srv_file_path = upload_rsp.json()
        print("srv_file", srv_file_path)
        assert DIRPATH in srv_file_path
