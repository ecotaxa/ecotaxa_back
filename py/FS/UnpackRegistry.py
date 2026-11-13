# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Registry of the archive unpackings in progress, shared between server processes.
# Each unpacking holds an flock on its entry, the lock dies with the process. So an
# entry which lock can be taken is from a dead process (restart, killed worker), and
# its staging folder, left in the user's files, can be removed and reported.
#
import contextlib
import datetime
import fcntl
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Set

from helpers.DynamicLogs import get_logger
from helpers.httpexception import DETAIL_UNPACK_INTERRUPTED

logger = get_logger(__name__)

SUFFIX = ".json"
TMP_SUFFIX = ".tmp"
# A temporary entry younger than this (s) may be about to be locked and published
TMP_GRACE = 60
# Entries held by this process. On NFS, flock is a per-process POSIX lock, so a
# sweep from the owning process would get the lock of a live entry.
_LIVE: Set[str] = set()
# The HTTP status of an interrupted unpacking, for status polling
INTERRUPTED_STATUS_CODE = 500


@contextlib.contextmanager
def registered(
    registry_dir: Optional[Path], info: Dict[str, Any]
) -> Generator[None, None, None]:
    """
    Register, while in the block, an unpacking described by info (staging, parent, name,
    user_id, upload_id). Best effort: a registry problem never prevents the unpacking.
    """
    entry: Optional[Path] = None
    fd: Optional[int] = None
    if registry_dir is not None:
        tmp_name = None
        try:
            registry_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=registry_dir, suffix=TMP_SUFFIX)
            fcntl.flock(fd, fcntl.LOCK_EX)
            data = dict(info, pid=os.getpid(), started=_now())
            os.write(fd, json.dumps(data).encode("utf-8"))
            # Published locked and complete, the lock follows the inode
            entry = registry_dir / (uuid.uuid4().hex + SUFFIX)
            os.replace(tmp_name, entry)
            _LIVE.add(str(entry))
        except Exception as e:
            logger.error("Could not register unpacking %s: %s", info, e)
            if tmp_name is not None:
                Path(tmp_name).unlink(missing_ok=True)
            if fd is not None:
                os.close(fd)
            fd, entry = None, None
    try:
        yield
    finally:
        if entry is not None:
            entry.unlink(missing_ok=True)
            _LIVE.discard(str(entry))
        if fd is not None:
            os.close(fd)


def sweep_stale(registry_dir: Path, users_files_dir: Path) -> int:
    """
    Clean up after the unpackings of dead processes: remove their staging folder, tell the
    user in an error file and in the upload status. Return the number of entries cleaned.
    Never raises for one entry.
    """
    if not registry_dir.is_dir():
        return 0
    ret = 0
    for an_entry in sorted(registry_dir.iterdir()):
        if str(an_entry) in _LIVE:
            continue
        if an_entry.name.endswith(TMP_SUFFIX):
            try:
                if time.time() - an_entry.stat().st_mtime < TMP_GRACE:
                    continue
            except OSError:
                continue
        elif not an_entry.name.endswith(SUFFIX):
            continue
        try:
            if _sweep_one(an_entry, users_files_dir):
                ret += 1
        except Exception as e:
            logger.error("Could not sweep unpack entry %s: %s", an_entry, e)
    return ret


def _sweep_one(entry: Path, users_files_dir: Path) -> bool:
    try:
        fd = os.open(entry, os.O_RDWR)
    except FileNotFoundError:
        return False  # Done meanwhile
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False  # Live
        if not entry.exists():
            return False  # Done, or swept by another process, meanwhile
        if entry.name.endswith(TMP_SUFFIX):
            entry.unlink(missing_ok=True)
            return False
        try:
            info = json.loads(entry.read_text())
        except ValueError:
            info = None
        if isinstance(info, dict):
            _clean_up(info, users_files_dir)
        else:
            logger.error("Unreadable unpack entry %s, dropped", entry)
        entry.unlink(missing_ok=True)
        return True
    finally:
        os.close(fd)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _clean_up(info: Dict[str, Any], users_files_dir: Path) -> None:
    """The unpacking described by info was interrupted, undo and report it"""
    # Late imports, these modules use this one
    from FS.UserFilesDir import UserFilesDirectory, PROGRESS_PREFIX
    from FS.UnpackStatus import UnpackStatus

    name = str(info.get("name", "?"))
    staging = Path(str(info.get("staging", "")))
    parent = Path(str(info.get("parent", "")))
    logger.warning("Unpacking of %s by process %s was interrupted", info, info.get("pid"))
    # Never trust the path blindly
    if staging.name.startswith(PROGRESS_PREFIX) and _inside(staging, users_files_dir):
        shutil.rmtree(staging, ignore_errors=True)
    else:
        logger.error("Not removing unexpected staging path %s", staging)
    message = "Extraction of '%s' failed, nothing was kept: %s" % (
        name,
        DETAIL_UNPACK_INTERRUPTED,
    )
    if parent.is_dir() and _inside(parent, users_files_dir):
        when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            UserFilesDirectory._error_file(parent, name).write_text(
                "%s UTC %s\n" % (when, message)
            )
        except OSError as e:
            logger.error("Could not report interrupted unpack of %s: %s", name, e)
    upload_id = info.get("upload_id")
    if upload_id:
        try:
            UnpackStatus(str(upload_id), int(info.get("user_id", -1)), name).update(
                {
                    "state": "error",
                    "status_code": INTERRUPTED_STATUS_CODE,
                    "message": message,
                }
            )
        except Exception as e:
            logger.error("Could not set status of interrupted unpack %s: %s", upload_id, e)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
