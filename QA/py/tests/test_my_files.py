# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exhibit some not-so-intuitive behavior of /my_files and associated upload
#
import gzip
import pathlib
import shutil
import time
import zipfile
import zlib
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
    if rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT:
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

        # 4. Remove the directory (moves it into trash)
        rsp = api_remove_user_file(fastapi, new_dir_name, CREATOR_AUTH)
        assert rsp.status_code == status.HTTP_200_OK

        # Verify it's gone from root
        list_rsp = fastapi.get(MY_FILES_URL + "/", headers=CREATOR_AUTH)
        entries = [e["name"] for e in list_rsp.json()["entries"]]
        assert new_dir_name not in entries

        # 5. Remove the file/dir already in trash (permanently deleted)
        trash_dir_name = f"trash.{CREATOR_USER_ID}"
        list_trash = fastapi.get(
            f"{MY_FILES_URL}{trash_dir_name}", headers=CREATOR_AUTH
        )
        assert list_trash.status_code == status.HTTP_200_OK
        trash_entries = [e["name"] for e in list_trash.json()["entries"]]
        assert new_dir_name in trash_entries

        # Remove the item already in trash
        rsp = api_remove_user_file(
            fastapi, f"{trash_dir_name}/{new_dir_name}", CREATOR_AUTH
        )
        assert rsp.status_code == status.HTTP_200_OK

        # Verify it is permanently removed from trash
        list_trash = fastapi.get(
            f"{MY_FILES_URL}{trash_dir_name}", headers=CREATOR_AUTH
        )
        assert list_trash.status_code == status.HTTP_200_OK
        trash_entries = [e["name"] for e in list_trash.json()["entries"]]
        assert new_dir_name not in trash_entries

        # 6. Move a directory to trash, then empty the whole trash
        dir_to_trash = "test_dir_to_empty"
        rsp = api_create_user_file(fastapi, dir_to_trash, CREATOR_AUTH)
        assert rsp.status_code == status.HTTP_200_OK
        api_create_user_file(fastapi, f"{dir_to_trash}/subfolder", CREATOR_AUTH)

        # Move directory to trash
        rsp = api_remove_user_file(fastapi, dir_to_trash, CREATOR_AUTH)
        assert rsp.status_code == status.HTTP_200_OK

        # Verify directory is in trash
        list_trash = fastapi.get(
            f"{MY_FILES_URL}{trash_dir_name}", headers=CREATOR_AUTH
        )
        assert list_trash.status_code == status.HTTP_200_OK
        trash_entries = [e["name"] for e in list_trash.json()["entries"]]
        assert dir_to_trash in trash_entries

        # Empty trash
        rsp = api_remove_user_file(fastapi, trash_dir_name, CREATOR_AUTH)
        assert rsp.status_code == status.HTTP_200_OK

        # Verify trash is now empty
        list_trash = fastapi.get(
            f"{MY_FILES_URL}{trash_dir_name}", headers=CREATOR_AUTH
        )
        assert list_trash.status_code == status.HTTP_200_OK
        assert len(list_trash.json()["entries"]) == 0

    finally:
        if dummy_file.exists():
            dummy_file.unlink()


def test_my_files_error_cases(fastapi, tmp_path):
    """
    Error cases for user files operations:
    - Damaged archives (corrupted archive upload)
    - Try to delete the trash directory
    - Move to existing target (place already taken by an existing file or directory)
    - Move file to existing dir (where target dir already contains the item)
    """
    # Clean user files first
    api_remove_user_file(fastapi, "*", CREATOR_AUTH)

    # 1. Damaged archives
    # Create corrupted zip: valid zip archive truncated/damaged so zipfile.is_zipfile is True but unpack fails
    valid_zip = tmp_path / "valid.zip"
    with zipfile.ZipFile(valid_zip, "w") as zf:
        zf.writestr("test1.tsv", "col1\tcol2\n1\t2\n")
        zf.writestr("test2.tsv", "col1\tcol2\n3\t4\n")
    zip_bytes = valid_zip.read_bytes()
    # Corrupt data inside the zip file while preserving header/footer structure so is_zipfile is true
    corrupted_zip = tmp_path / "corrupted.zip"
    corrupted_zip.write_bytes(zip_bytes[:30] + b"\x00" * 20 + zip_bytes[50:])
    with open(corrupted_zip, "rb") as fin:
        with pytest.raises(zipfile.BadZipFile):
            fastapi.post(
                MY_FILES_URL,
                headers=CREATOR_AUTH,
                data={"path": "corrupted.zip"},
                files={"file": fin},
            )

    # Corrupted gzip archive: valid 2-byte header \x1f\x8b so _is_gz is True, but corrupted gzip stream
    corrupted_gz = tmp_path / "corrupted.tsv.gz"
    corrupted_gz.write_bytes(
        b"\x1f\x8b\x08\x00corrupted_gzip_content_not_valid_gzip_stream"
    )
    with open(corrupted_gz, "rb") as fin:
        with pytest.raises((gzip.BadGzipFile, zlib.error)):
            fastapi.post(
                MY_FILES_URL,
                headers=CREATOR_AUTH,
                data={"path": "corrupted.tsv.gz"},
                files={"file": fin},
            )

    # 2. Try to delete / move the trash directory or manipulate protected trash
    trash_dir_name = f"trash.{CREATOR_USER_ID}"
    # Trying to move the trash directory -> 422
    rsp = api_move_user_file(fastapi, trash_dir_name, "renamed_trash", CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Trying to move into trash directory directly -> 422
    rsp = api_move_user_file(fastapi, "file1.txt", trash_dir_name, CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Trying to create inside trash directory -> 422
    rsp = api_create_user_file(fastapi, f"{trash_dir_name}/new_dir", CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # 3. Move a file to a place already taken by an existing file
    api_upload_file(
        fastapi,
        str(valid_zip),
        "test_files/valid.zip",
        CREATOR_AUTH,
    )
    # Both valid/test1.tsv and valid/test2.tsv exist as individual files
    file1 = "test_files/valid/test1.tsv"
    file2 = "test_files/valid/test2.tsv"
    # Moving file1 to file2 where file2 already exists as a file -> 422
    rsp = api_move_user_file(fastapi, file1, file2, CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # 4. Move to existing target directory
    # Create two directories: dir1 and dir2, and put an item inside dir2
    dir1 = "test_dir_source"
    dir2 = "test_dir_target"
    api_create_user_file(fastapi, dir1, CREATOR_AUTH)
    api_create_user_file(fastapi, dir2, CREATOR_AUTH)
    api_create_user_file(fastapi, f"{dir2}/{dir1}", CREATOR_AUTH)

    # Moving dir1 into dir2 when dir2 already contains dir1 -> 422
    rsp = api_move_user_file(fastapi, dir1, dir2, CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # 5. Move file to existing dir (where target dir already contains an entry with the same stem)
    parent_dir = "test_parent_dir"
    api_create_user_file(fastapi, parent_dir, CREATOR_AUTH)
    # Create a subfolder inside parent_dir with name 'item1'
    api_create_user_file(fastapi, f"{parent_dir}/item1", CREATOR_AUTH)
    # Create a folder in root with name 'item1'
    api_create_user_file(fastapi, "item1", CREATOR_AUTH)

    # Moving 'item1' into parent_dir where parent_dir/item1 already exists -> 422
    rsp = api_move_user_file(fastapi, "item1", parent_dir, CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Clean up after test
    api_remove_user_file(fastapi, "*", CREATOR_AUTH)
