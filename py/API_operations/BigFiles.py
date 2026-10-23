# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
import asyncio
import contextlib
import os
import shutil
from pathlib import Path
from typing import Callable, Dict, Any, Set, Optional

from fastapi import Depends, Request
from tuspyserver import create_tus_router
from tuspyserver.file import _validate_uid_within_dir
from tuspyserver.lock import acquire_upload_lock
from tuspyserver.storage.local import LocalFileStorage

from FS.UserFilesDir import UserFilesDirectory
from helpers.AppConfig import Config
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import get_current_user

TUS_PREFIX = "/user_files/upload"


logger = get_logger(__name__)

background_tasks: Set[asyncio.Task[Any]] = set()


def get_tus_files_dir() -> str:
    """
    Get the directory where big files are stored.
    Use a subfolder of the users files area.
    """
    base_dir = Config().get_users_files_dir()
    tus_dir = Path(base_dir, "tus_uploads")
    tus_dir.mkdir(parents=True, exist_ok=True)
    return str(tus_dir)


async def tus_auth(
    request: Request, current_user: int = Depends(get_current_user)
) -> None:
    """
    TUS authentication dependency.
    It attaches the user id to the request state for further use in hooks.
    """
    logger.info("TUS auth: current_user=%s", current_user)
    request.state.current_user_id = current_user
    return None


async def _background_unpack(
    user_dir: UserFilesDirectory, file_path: Path, dest_dir: Path
) -> None:
    try:
        user_dir.switch_to_progress_marking()
        await asyncio.to_thread(
            user_dir.dispatch_unpack, compressed_path=file_path, to_path=dest_dir
        )
        logger.info("Done unpacking %s in background", file_path)
    except Exception as e:
        logger.error(
            "Error unpacking %s in background: %s", file_path, str(e), exc_info=True
        )
        raise


async def on_tus_upload_complete(
    file_path: str, metadata: Dict[str, Any], current_user_id: int
) -> None:
    """
    Treat the uploaded file so it ends up in the user's files directory.
    """
    logger.info(
        "TUS on_tus_upload_complete: file_path=%s, user=%s, metadata=%s",
        file_path,
        current_user_id,
        metadata,
    )
    try:
        # e.g. /mnt/tus_uploads/fd8d989adda14069ba8495a71af1d6b8
        tus_path = Path(file_path)

        # metadata contains 'filename' if provided by client (Upload-Metadata header)
        original_name = metadata.get("filename")
        if original_name is None:
            original_name = tus_path.name  # Hum, unlikely
        else:
            # Ensure no directory traversal
            original_name = os.path.basename(original_name)

        user_dir = UserFilesDirectory(current_user_id)
        dest_dir = destination_directory(user_dir, metadata.get("path"))
        dest_path = dest_dir / original_name

        if user_dir.is_compressed(tus_path):
            tus_path = tus_path.rename(dest_path)
            task = asyncio.create_task(
                _background_unpack(user_dir, tus_path, dest_dir.absolute()),
                name=f"unpack_{original_name}",
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)
            logger.info("TUS file upload complete: uncompressing into %s ", dest_dir)
            try:
                # Wait for 2 minutes max, to give impression it's sync for small archives
                await asyncio.wait_for(task, timeout=120)
                logger.info("TUS file upload unpack done into %s ", dest_dir)
            except TimeoutError:
                logger.info("TUS file upload unpack CONTINUES into %s ", dest_dir)
        else:
            # Plain uncompressed file case, should not happen with EcoTaxa client which always sends a zip
            stem = Path(original_name).stem
            suffix = Path(original_name).suffix
            counter = 1
            while dest_path.is_dir():
                logger.warning(
                    "Destination %s is a directory, appending suffix to filename",
                    dest_path,
                )
                new_name = f"{stem}_{counter}{suffix}"
                dest_path = dest_dir / new_name
                counter += 1
            if dest_path.exists():  # Always a file due to above
                logger.info(
                    "Destination file %s already exists, overwriting", dest_path
                )
            shutil.move(tus_path, str(dest_path))
            # Keep policy to exclude unwanted files.
            user_dir.dispatch_unpack(tus_path, dest_path)
            logger.info(
                "TUS file upload complete: moved %s to %s", file_path, dest_path
            )
    except Exception as e:
        logger.error("Error in on_tus_upload_complete: %s", str(e))
        # Depending on tuspyserver, raising here might or might not be handled.
        # But we should at least log it.


def destination_directory(
    user_dir: UserFilesDirectory, client_path: Optional[str]
) -> Path:
    dest_dir = user_dir._root_path

    # Metadata may carry the client-side destination sub-path, e.g.
    # "some/sub/dir/<filename>" (see js-dirtozip.js sendZipFile).
    # It mirrors what UserFilesDirectory.add_file() does for the non-TUS
    # upload path: strip the trailing filename to get the target dir.
    if client_path is not None:
        client_dir = os.path.dirname(client_path)
        client_dir = client_dir.lstrip(os.path.sep)
        parts = [p for p in Path(client_dir).parts if p not in (".", "")]
        if ".." in parts:
            logger.warning(
                "TUS upload rejected path traversal attempt: %s", client_path
            )
        elif parts:
            dest_dir = dest_dir.joinpath(*parts)
    user_dir.ensure_exists(dest_dir)
    return dest_dir


async def get_on_complete_handler(
    request: Request,
) -> Callable[[str, Dict[str, Any]], Any]:
    """
    Dependency that returns the completion handler with the current user id.
    """
    current_user_id = getattr(request.state, "current_user_id", None)
    logger.info("get_on_complete_handler: current_user_id=%s", current_user_id)
    if current_user_id is None:
        # This should not happen if tus_auth was called
        logger.error(
            "current_user_id not found in request state in get_on_complete_handler"
        )
        return lambda *_: None

    return lambda file_path, metadata: on_tus_upload_complete(
        file_path, metadata, current_user_id
    )


class SplitLocalFileStorage(LocalFileStorage):
    """
    Hybrid TUS Storage implementing tuspyserver.storage.TusStorage interface.
    - Metadata (.info) and locks -> Local /tmp directory (OverlayFS)
    - Heavy payload data files   -> GPFS / NFS mount / ordinary FS
    """

    def __init__(self, files_dir: str, info_dir: str):
        super().__init__(files_dir)
        self.info_dir = info_dir
        Path(info_dir).mkdir(parents=True, exist_ok=True)
        self.locks_dir = os.path.join(self.info_dir, ".locks")
        Path(self.locks_dir).mkdir(parents=True, exist_ok=True)

    def _info_path(self, uid: str) -> str:
        """Redirects .info metadata files to the local container filesystem."""
        _validate_uid_within_dir(self.info_dir, uid)
        return os.path.join(self.info_dir, f"{uid}.info")

    @contextlib.asynccontextmanager
    async def lock(self, uid: str):  # type: ignore
        """Advisory file lock, shared with any other process using this dir."""
        path = self._path(uid)
        cm = await asyncio.to_thread(
            lambda: acquire_upload_lock(path, locks_dir=self.locks_dir, blocking=True)
        )
        await asyncio.to_thread(cm.__enter__)
        try:
            yield
        finally:
            await asyncio.to_thread(cm.__exit__, None, None, None)


hybrid_storage = SplitLocalFileStorage(
    files_dir=get_tus_files_dir(),
    info_dir="/tmp/tus_info_scratch",
)


def create_big_files_router():
    """
    Create the TUS router for big files.
    """
    return create_tus_router(
        prefix=TUS_PREFIX,
        storage=hybrid_storage,
        max_size=Config().get_max_upload_size(),  # Same as client
        auth=tus_auth,
        upload_complete_dep=get_on_complete_handler,
        tags=["MyFiles"],
    )
