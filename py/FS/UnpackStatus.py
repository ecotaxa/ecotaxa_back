# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Status of the unpacking of a TUS upload, shared between server processes via a small JSON
# file next to the upload, so a client can poll it from any worker.
#
import datetime
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from FS.UserFilesDir import get_tus_files_dir
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

# TUS upload ids are uuid4().hex
_UPLOAD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class UnpackStatus(object):
    """
    Writer and reader of the status of one upload unpacking.
    """

    SUFFIX = ".unpack.json"
    # Minimum delay between two writes, unless the state changes
    MIN_INTERVAL = 0.5

    def __init__(self, upload_id: str, user_id: int, name: str):
        self.path = self.path_for(upload_id)
        self.base: Dict[str, Any] = {"user_id": user_id, "name": name}
        self._last_write = 0.0
        self._last_state: Optional[str] = None

    @classmethod
    def path_for(cls, upload_id: str) -> Path:
        if not _UPLOAD_ID_RE.match(upload_id):
            raise ValueError("Invalid upload id")
        return Path(get_tus_files_dir(), upload_id + cls.SUFFIX)

    def update(self, fields: Dict[str, Any]) -> None:
        """
        Write the status, at most every MIN_INTERVAL seconds unless the state changes. Never raises.
        """
        state = fields.get("state")
        now = time.monotonic()
        if state == self._last_state and now - self._last_write < self.MIN_INTERVAL:
            return
        data = dict(self.base)
        data.update(fields)
        data["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            self._write_atomic(data)
        except Exception as e:
            logger.error("Could not write unpack status %s: %s", self.path, e)
            return
        self._last_write = now
        self._last_state = state

    def _write_atomic(self, data: Dict[str, Any]) -> None:
        # Readers in other processes see the previous version or this one, never a partial file
        fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fout:
                json.dump(data, fout)
            os.replace(tmp_name, self.path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    @classmethod
    def read(cls, upload_id: str) -> Optional[Dict[str, Any]]:
        """The last written status, or None if unknown"""
        try:
            path = cls.path_for(upload_id)
            return json.loads(path.read_text())
        except (ValueError, OSError):
            return None
