# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exhibit some not-so-intuitive behavior of /my_files and associated upload
#
import pathlib
import shutil
import time
from typing import Dict

import pytest
from starlette import status

from tests.credentials import CREATOR_AUTH, CREATOR_USER_ID
from tests.api_wrappers import (
    api_file_import,
    api_wait_for_stable_job,
    api_check_job_errors,
    MY_FILES_URL,
    api_upload_file,
    api_check_job_ok,
    api_remove_user_file,
    api_move_user_file,
    api_create_user_file,
)
from tests.test_import import (
    SHARED_DIR,
    V6_FILE,
    create_project,
)

SEPARATOR = "/"
DIRPATH = "XXX"


@pytest.mark.parametrize("title", ["Try my files"])
def test_my_files(fastapi, tstlogs, title):
    """
    Simple import with no fixed values at all, but using the upload directory.
    """
    prj_id = create_project(CREATOR_USER_ID, title)

    DEST_FILE_NAME = "LOKI_46-24hours_01.zip"
    DEST_DIR_NAME = "LOKI_46-24hours_01"

    # Copy an existing test file into current dir, simulating client side
    shutil.copyfile(SHARED_DIR / V6_FILE, tstlogs / DEST_FILE_NAME)
    # Upload this file
    remote_path = api_upload_file(
        fastapi,
        tstlogs / DEST_FILE_NAME,
        DIRPATH + SEPARATOR + DEST_FILE_NAME,
        CREATOR_AUTH,
    )
    assert DIRPATH in remote_path  # The subdirectory was created

    # And another
    DEST_FILE_NAME2 = "readme.txt"
    # Copy an existing test file into current dir, simulating client side
    shutil.copyfile(SHARED_DIR / "HOWTO.txt", tstlogs / DEST_FILE_NAME2)
    # Upload this file
    api_upload_file(
        fastapi,
        tstlogs / DEST_FILE_NAME2,
        DIRPATH + SEPARATOR + DEST_FILE_NAME2,
        CREATOR_AUTH,
    )
    assert DIRPATH in remote_path  # The subdirectory was created

    # The pathparam becomes a top-level directory
    list_rsp = fastapi.get(MY_FILES_URL + SEPARATOR, headers=CREATOR_AUTH)
    assert list_rsp.status_code == 200
    my_files_root: Dict = list_rsp.json()
    assert my_files_root["path"] == ""
    assert {
        "mtime": "",
        "name": DIRPATH,
        "size": 0,
        "type": "D",
    } in my_files_root["entries"]

    # The files are stored in the subdirectory
    DIRDEST = DIRPATH + SEPARATOR + DEST_DIR_NAME
    list_rsp = fastapi.get(MY_FILES_URL + SEPARATOR + DIRDEST, headers=CREATOR_AUTH)
    assert list_rsp.status_code == 200
    my_files_subdir: Dict = list_rsp.json()
    assert my_files_subdir["path"] == DIRDEST
    assert (
        len(my_files_subdir["entries"]) == 1
    )  # The second file being .txt will have size 0 on re-read

    # Import the file without the right path -> Error
    req = {"source_path": DEST_FILE_NAME}
    rsp = api_file_import(fastapi, prj_id, req, auth=CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    api_wait_for_stable_job(fastapi, job_id)
    errors = api_check_job_errors(fastapi, job_id)
    assert "FileNotFoundError" in "".join(errors)

    req = {"source_path": DIRDEST}
    rsp = api_file_import(fastapi, prj_id, req, auth=CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    api_wait_for_stable_job(fastapi, job.id)
    api_check_job_ok(fastapi, job.id)


@pytest.mark.parametrize(
    "archive_name",
    [
        "cont.tar",
        "cont.gz",
        "cont.zip",
        # "ecotaxa_b_da_19.tsv.gz", # TODO: Is removed after decomp, magic_rs does not know
        # "ecotaxa_b_da_19.csv.gz",
        "x2EA0yD7AwC7h13F.png.gz",
    ],
)
def test_upload_archives(fastapi, archive_name):
    """
    Upload each of the hardcoded archive files and verify.
    """
    archive = SHARED_DIR / "my_files" / archive_name
    assert archive.exists()

    dest_dir = archive_name.replace(".", "_")
    remote_sub_dir = f"test_archives_{dest_dir}"

    dest_path = remote_sub_dir + SEPARATOR + archive.name
    api_upload_file(
        fastapi,
        archive,
        dest_path,
        CREATOR_AUTH,
    )

    # Verify something was uploaded/extracted
    list_rsp = fastapi.get(
        MY_FILES_URL + SEPARATOR + remote_sub_dir, headers=CREATOR_AUTH
    )
    assert list_rsp.status_code == 200
    entries = list_rsp.json()["entries"]
    assert len(entries) > 0

    api_remove_user_file(fastapi, "*", CREATOR_AUTH)


def test_user_file_operations(fastapi):
    # 1. Create a directory
    dir_name = "test_dir_unique_" + str(int(time.time()))
    rsp = api_create_user_file(fastapi, dir_name, CREATOR_AUTH)
    if rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        print(rsp.json())
    assert rsp.status_code == status.HTTP_200_OK
    assert dir_name in rsp.json()

    # Verify it exists
    list_rsp = fastapi.get(MY_FILES_URL + "/", headers=CREATOR_AUTH)
    assert list_rsp.status_code == status.HTTP_200_OK
    entries = [e["name"] for e in list_rsp.json()["entries"]]
    assert dir_name in entries

    # 2. Upload a file into it
    dummy_file = pathlib.Path("dummy.txt")
    dummy_file.write_text("hello")
    try:
        remote_path = api_upload_file(
            fastapi, str(dummy_file), dir_name + "/dummy.txt", CREATOR_AUTH
        )
        assert dir_name + "/dummy.txt" in remote_path

        # 3. Move/Rename the directory
        new_dir_name = "test_dir_moved"
        rsp = api_move_user_file(fastapi, dir_name, new_dir_name, CREATOR_AUTH)
        assert rsp.status_code == status.HTTP_200_OK

        # Verify old name is gone, new name exists
        list_rsp = fastapi.get(MY_FILES_URL + "/", headers=CREATOR_AUTH)
        entries = [e["name"] for e in list_rsp.json()["entries"]]
        assert dir_name not in entries
        assert new_dir_name in entries

        # 4. Remove the directory
        rsp = api_remove_user_file(fastapi, new_dir_name, CREATOR_AUTH)
        assert rsp.status_code == status.HTTP_200_OK

        # Verify it's gone
        list_rsp = fastapi.get(MY_FILES_URL + "/", headers=CREATOR_AUTH)
        entries = [e["name"] for e in list_rsp.json()["entries"]]
        assert new_dir_name not in entries

    finally:
        if dummy_file.exists():
            dummy_file.unlink()
