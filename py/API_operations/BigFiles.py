# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

import os
import shutil
from pathlib import Path
from typing import Callable, Dict, Any

from fastapi import Depends, Request

from FS.UserFilesDir import UserFilesDirectory
from helpers.AppConfig import Config
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import get_current_user
from helpers.tuspyserver import create_tus_router

logger = get_logger(__name__)


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


def on_tus_upload_complete(
    file_path: str, metadata: Dict[str, Any], current_user_id: int
):
    """
    Move the uploaded file to the user's files directory.
    """
    logger.info(
        "TUS on_tus_upload_complete: file_path=%s, user=%s, metadata=%s",
        file_path,
        current_user_id,
        metadata,
    )
    try:
        # metadata contains 'filename' if provided by client (Upload-Metadata header)
        original_name = metadata.get("filename")
        if not original_name:
            original_name = Path(file_path).name

        # Ensure no directory traversal
        original_name = os.path.basename(original_name)

        user_dir = UserFilesDirectory(current_user_id)
        dest_dir = user_dir._root_path
        user_dir.ensure_exists(dest_dir)

        dest_path = dest_dir / original_name

        # Handle existing files
        if dest_path.exists():
            # If it's a directory, we can't overwrite it with a file
            if dest_path.is_dir():
                logger.warning(
                    "Destination %s is a directory, cannot move TUS upload", dest_path
                )
                # Append a suffix to the filename
                original_name = f"{original_name}_1"
                dest_path = dest_dir / original_name
            else:
                # If it's a file, we overwrite it (existing behavior of shutil.move)
                logger.info("Destination %s already exists, overwriting", dest_path)

        shutil.move(file_path, str(dest_path))
        logger.info("TUS upload complete: moved %s to %s", file_path, dest_path)

        # Trigger unpacking if it's an archive, similar to UserFilesDirectory.add_file
        # TODO: UserFilesDirectory should probably have a method to handle a local file
        # as if it was uploaded.
        file_ext, compressed_path, mime_type = user_dir._get_file_info(
            original_name, dest_dir.absolute()
        )
        logger.info(
            "TUS post-process: original_name=%s, mime_type=%s, compressed_path=%s",
            original_name,
            mime_type,
            compressed_path,
        )
        user_dir.compressed_origin = compressed_path
        user_dir.dispatch_unpack(compressed_path, dest_dir.absolute())
    except Exception as e:
        logger.error("Error in on_tus_upload_complete: %s", str(e))
        # Depending on tuspyserver, raising here might or might not be handled.
        # But we should at least log it.


async def get_on_complete_handler(
    request: Request,
) -> Callable[[str, Dict[str, Any]], None]:
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


def create_big_files_router():
    """
    Create the TUS router for big files.
    """
    return create_tus_router(
        prefix="/big_files/upload",
        files_dir=get_tus_files_dir(),
        max_size=Config().get_max_upload_size(),  # Same as client
        auth=tus_auth,
        upload_complete_dep=get_on_complete_handler,
        tags=["MyFiles"],
    )
