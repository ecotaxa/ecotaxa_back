# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Tuple

from API_operations.helpers.Service import Service
from FS.Vault import Vault
from helpers.fastApiUtils import AutoCloseBinaryIO


class ImageService(Service):
    """
    Minimal image server.
    """

    def __init__(self) -> None:
        super().__init__()
        self.vault = Vault(self.config.vault_dir())

    def get_stream(
        self, dir_id: str, img_in_dir: str
    ) -> Tuple[AutoCloseBinaryIO, int, str]:
        file_path = self.vault.image_path("%s/%s" % (dir_id, img_in_dir))
        fp = AutoCloseBinaryIO(file_path)
        media_type = "text/plain"
        img_in_dir_lower = img_in_dir.lower()
        if img_in_dir_lower.endswith(".jpg"):
            media_type = "image/jpeg"
        elif img_in_dir_lower.endswith(".png"):
            media_type = "image/png"
        return fp, fp.size(), media_type
