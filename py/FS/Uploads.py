# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Where uploads from TUS are stored before processing
#
from pathlib import Path

from helpers.AppConfig import Config


def get_tus_files_dir() -> str:
    """
    Get the directory where uploaded files (via TUS) are stored.
    Use a subfolder of the users files area.
    """
    base_dir = Config().get_users_files_dir()
    tus_dir = Path(base_dir, "tus_uploads")
    tus_dir.mkdir(parents=True, exist_ok=True)
    return str(tus_dir)
