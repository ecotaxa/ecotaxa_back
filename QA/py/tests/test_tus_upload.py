# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import base64
from typing import Dict

from starlette import status

from tests.api_wrappers import MY_FILES_URL, api_remove_user_file
from tests.consts import SHARED_DIR, V6_FILE
from tests.credentials import CREATOR_AUTH, USER_AUTH

TUS_UPLOAD_URL = "/user_files/upload/"
TUS_VERSION = "1.0.0"


def _encode_metadata(metadata: Dict[str, str]) -> str:
    """Encode key-value metadata pairs for the Upload-Metadata TUS header."""
    pairs = []
    for k, v in metadata.items():
        b64_val = base64.b64encode(v.encode("utf-8")).decode("ascii")
        pairs.append(f"{k} {b64_val}")
    return ", ".join(pairs)


def test_tus_upload_protocol(fastapi):
    """
    Exercise basic TUS protocol flow:
    1. OPTIONS: protocol discovery
    2. POST: create upload resource with length and metadata
    3. HEAD: check initial offset
    4. PATCH: upload data in chunks
    5. Verify the uploaded archive is unpacked and placed in user files
    """
    api_remove_user_file(fastapi, "*", CREATOR_AUTH)

    # 1. OPTIONS discovery
    res_options = fastapi.options(TUS_UPLOAD_URL, headers=CREATOR_AUTH)
    assert res_options.status_code == status.HTTP_204_NO_CONTENT
    assert res_options.headers.get("Tus-Resumable") == TUS_VERSION
    assert TUS_VERSION in res_options.headers.get("Tus-Version", "")

    # 2. POST to initiate upload using UVP6_example.zip
    zip_bytes = (SHARED_DIR / V6_FILE).read_bytes()
    archive_name = V6_FILE.name
    extracted_folder = V6_FILE.stem
    metadata_str = _encode_metadata(
        {
            "filename": archive_name,
            "filetype": "application/zip",
            "path": "my_folder/uvp6",
        }
    )

    create_headers = {
        "Tus-Resumable": TUS_VERSION,
        "Upload-Length": str(len(zip_bytes)),
        "Upload-Metadata": metadata_str,
        **CREATOR_AUTH,
    }
    res_post = fastapi.post(TUS_UPLOAD_URL, headers=create_headers)
    assert res_post.status_code == status.HTTP_201_CREATED
    assert res_post.headers.get("Tus-Resumable") == TUS_VERSION

    location = res_post.headers.get("Location")
    assert location is not None
    assert location.startswith("/")
    upload_url = location

    # 3. HEAD to verify initial offset is 0
    res_head = fastapi.head(
        upload_url, headers={"Tus-Resumable": TUS_VERSION, **CREATOR_AUTH}
    )
    assert res_head.status_code == status.HTTP_200_OK
    assert res_head.headers.get("Upload-Offset") == "0"
    assert res_head.headers.get("Upload-Length") == str(len(zip_bytes))

    # 4. PATCH chunk 1
    chunk_size = len(zip_bytes) // 2
    chunk1 = zip_bytes[:chunk_size]
    chunk2 = zip_bytes[chunk_size:]

    patch1_headers = {
        "Tus-Resumable": TUS_VERSION,
        "Content-Type": "application/offset+octet-stream",
        "Upload-Offset": "0",
        **CREATOR_AUTH,
    }
    res_patch1 = fastapi.patch(upload_url, headers=patch1_headers, content=chunk1)
    assert res_patch1.status_code == status.HTTP_204_NO_CONTENT
    assert res_patch1.headers.get("Upload-Offset") == str(chunk_size)

    # 5. HEAD to verify intermediate offset
    res_head = fastapi.head(
        upload_url, headers={"Tus-Resumable": TUS_VERSION, **CREATOR_AUTH}
    )
    assert res_head.status_code == status.HTTP_200_OK
    assert res_head.headers.get("Upload-Offset") == str(chunk_size)

    # 6. PATCH chunk 2 (completes upload)
    patch2_headers = {
        "Tus-Resumable": TUS_VERSION,
        "Content-Type": "application/offset+octet-stream",
        "Upload-Offset": str(chunk_size),
        **CREATOR_AUTH,
    }
    res_patch2 = fastapi.patch(upload_url, headers=patch2_headers, content=chunk2)
    assert res_patch2.status_code == status.HTTP_204_NO_CONTENT
    assert res_patch2.headers.get("Upload-Offset") == str(len(zip_bytes))

    # 7. Check user files directory contains the unpacked folder
    res_files = fastapi.get(MY_FILES_URL + "/my_folder", headers=CREATOR_AUTH)
    assert res_files.status_code == status.HTTP_200_OK
    entries = res_files.json()["entries"]
    assert extracted_folder in [e["name"] for e in entries]

    api_remove_user_file(fastapi, "*", CREATOR_AUTH)


def _tus_upload(fastapi, content: bytes, filename: str, path: str) -> str:
    """Upload content in a single PATCH, return the upload id"""
    metadata_str = _encode_metadata({"filename": filename, "path": path})
    res_post = fastapi.post(
        TUS_UPLOAD_URL,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Upload-Length": str(len(content)),
            "Upload-Metadata": metadata_str,
            **CREATOR_AUTH,
        },
    )
    assert res_post.status_code == status.HTTP_201_CREATED
    res_patch = fastapi.patch(
        res_post.headers["Location"],
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": "0",
            **CREATOR_AUTH,
        },
        content=content,
    )
    assert res_patch.status_code == status.HTTP_204_NO_CONTENT
    return res_post.headers["Location"].rstrip("/").split("/")[-1]


def _names_in(fastapi, folder: str):
    res_files = fastapi.get(MY_FILES_URL + "/" + folder, headers=CREATOR_AUTH)
    assert res_files.status_code == status.HTTP_200_OK
    return sorted(e["name"] for e in res_files.json()["entries"])


def test_tus_upload_plain_files(fastapi):
    """
    Files which are not archives go through the same type check as archive members:
    text data is kept, other unaccepted types are removed, with an explanation file.
    """
    api_remove_user_file(fastapi, "*", CREATOR_AUTH)
    _tus_upload(fastapi, b"object_id\n[t]\nobj1\n", "ecotaxa_a.tsv", "plain/x")
    _tus_upload(fastapi, b"\x7fELF\x02\x01" + b"\x00" * 64, "evil.bin", "plain/x")
    assert _names_in(fastapi, "plain") == [
        "ecotaxa_a.tsv",
        "evil.bin.unpack_error.txt",
    ]
    api_remove_user_file(fastapi, "*", CREATOR_AUTH)


UNPACK_STATUS_URL = "/user_files/unpack_status/{upload_id}"


def _zip(members: Dict[str, bytes]) -> bytes:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)
    return buf.getvalue()


def _status_of(fastapi, upload_id: str, auth=CREATOR_AUTH):
    return fastapi.get(UNPACK_STATUS_URL.format(upload_id=upload_id), headers=auth)


def test_tus_unpack_status(fastapi):
    """The status of an upload unpacking can be polled, by its uploader only."""
    api_remove_user_file(fastapi, "*", CREATOR_AUTH)
    tsv = b"object_id\n[t]\nobj1\n"
    inner = _zip({"ecotaxa_s1.tsv": tsv})
    # Archive with a nested one
    upload_id = _tus_upload(
        fastapi, _zip({"a.tsv": tsv, "s1_Images.zip": inner}), "st.zip", "st_dir/x"
    )
    rsp = _status_of(fastapi, upload_id)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    got = rsp.json()
    assert got["state"] == "done" and got["percent"] == 100
    assert got["name"] == "st.zip"
    assert got["result_paths"] == ["st_dir/st"]
    assert got["entries_total"] == 2 and got["files_done"] == 3
    assert "Retry-After" not in rsp.headers
    assert "user_id" not in got
    # Corrupt archive
    good = _zip({"a.tsv": tsv * 100})
    upload_id = _tus_upload(
        fastapi, good[:40] + b"\x00" * 40 + good[80:], "bad.zip", "st_dir/x"
    )
    got = _status_of(fastapi, upload_id).json()
    assert got["state"] == "error"
    assert "Archive is corrupt" in got["message"]
    # Not archives
    upload_id = _tus_upload(fastapi, tsv, "ecotaxa_p.tsv", "st_dir/x")
    got = _status_of(fastapi, upload_id).json()
    assert got["state"] == "done" and got["result_paths"] == ["st_dir/ecotaxa_p.tsv"]
    upload_id = _tus_upload(fastapi, b"\x7fELF\x02\x01" + b"\x00" * 64, "e.bin", "st_dir/x")
    got = _status_of(fastapi, upload_id).json()
    assert got["state"] == "error"
    # Another user, an unknown or invalid id: 404
    assert _status_of(fastapi, upload_id, USER_AUTH).status_code == 404
    assert _status_of(fastapi, "0" * 32).status_code == 404
    assert _status_of(fastapi, "..%2F..%2Fetc").status_code == 404
    api_remove_user_file(fastapi, "*", CREATOR_AUTH)


def test_tus_unpack_status_while_unpacking(fastapi, monkeypatch):
    """While unpacking: state unpacking, with Retry-After."""
    from FS.UnpackStatus import UnpackStatus

    status_obj = UnpackStatus("1" * 32, 3, "x.zip")
    monkeypatch.setattr(UnpackStatus, "MIN_INTERVAL", 0)
    from tests.credentials import CREATOR_USER_ID

    status_obj.base["user_id"] = CREATOR_USER_ID
    status_obj.update({"state": "unpacking", "percent": 42})
    rsp = _status_of(fastapi, "1" * 32)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["state"] == "unpacking" and rsp.json()["percent"] == 42
    assert rsp.headers["Retry-After"] == "2"
    status_obj.path.unlink()
