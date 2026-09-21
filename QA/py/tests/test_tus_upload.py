# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import base64
from typing import Dict

from starlette import status

from tests.api_wrappers import MY_FILES_URL, api_remove_user_file
from tests.consts import SHARED_DIR, V6_FILE
from tests.credentials import CREATOR_AUTH

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
    upload_url = (
        location if location.startswith("/") else "/" + location.split("/", 3)[-1]
    )

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
