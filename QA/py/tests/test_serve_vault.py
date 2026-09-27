# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import pytest
from pathlib import Path
from starlette import status

from FS.Vault import Vault
from helpers.AppConfig import Config
from test_import import SHARED_DIR

IMAGES_DIR = SHARED_DIR / "images"
TEST_PNG = IMAGES_DIR / "0128.png"
TEST_JPG = IMAGES_DIR / "9990.jpg"


@pytest.mark.parametrize(
    "img_path, img_id, expected_content_type",
    [
        (TEST_PNG, 100, "image/png"),
        (TEST_JPG, 200, "image/jpeg"),
    ],
)
def test_vault_endpoint(fastapi, img_path, img_id, expected_content_type):
    vault_dir = Path(Config().vault_dir())
    vault = Vault(str(vault_dir))

    sub_path = vault.store_image(img_path, img_id)
    dir_id, img_in_dir = sub_path.split("/")

    url = f"/vault/{dir_id}/{img_in_dir}"
    response = fastapi.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert expected_content_type in response.headers["content-type"]
    assert response.headers["content-length"] == str(img_path.stat().st_size)
    assert response.content == img_path.read_bytes()
