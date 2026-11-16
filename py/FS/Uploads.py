# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Where uploads from TUS are stored before processing
#
import os
from pathlib import Path
from typing import Optional

from helpers.AppConfig import Config

# Marker telling that the upload was already treated by the completion hook
CLAIM_SUFFIX = ".claimed"


def get_tus_files_dir() -> str:
    """
    Get the directory where uploaded files (via TUS) are stored.
    Use a subfolder of the users files area.
    """
    base_dir = Config().get_users_files_dir()
    tus_dir = Path(base_dir, "tus_uploads")
    tus_dir.mkdir(parents=True, exist_ok=True)
    return str(tus_dir)


def claim_upload(upload_id: str) -> Optional[Path]:
    """
    Claim the treatment of a completed TUS upload, so that it happens only once.
    The claim is a file next to the upload, created atomically with O_EXCL, hence
    shared by all the server processes. Return the claim, or None if another call
    already owns it. The nightly cleanup removes it along with the upload.
    """
    claim = Path(get_tus_files_dir(), upload_id + CLAIM_SUFFIX)
    try:
        fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return None
    try:
        os.write(fd, ("pid %d\n" % os.getpid()).encode("ascii"))
    finally:
        os.close(fd)
    return claim


def release_claim(claim: Path) -> None:
    """Release a claim, after a failure, so that the upload can be treated again."""
    claim.unlink(missing_ok=True)
