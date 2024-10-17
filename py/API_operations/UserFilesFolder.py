# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Per-user or shared set of files.
#
import time
from os import path as ospath
from typing import Optional, Union
from fastapi import UploadFile
from pathlib import Path
from API_models.filesystem import DirectoryEntryModel, DirectoryModel
from BO.Rights import RightsBO, NOT_AUTHORIZED
from BO.User import UserIDT
from DB.User import User
from FS.UserFilesDir import UserFilesDirectory
from FS.CommonDir import CommonFolder
from helpers.DynamicLogs import get_logger
from .helpers.Service import Service
from fastapi import HTTPException

logger = get_logger(__name__)


class UserFilesFolderService(Service):
    """
    A service for storing/cleaning user specific folders.
    """

    def __init__(self) -> None:
        super().__init__()

    def _can_use_dir_throw(self, path: str, exclude_path: Optional[list] = None) -> str:
        excludes = [".", "..", ""]
        if exclude_path is not None:
            excludes.extend(exclude_path)
        if path not in excludes:
            return path.lstrip(ospath.sep)
        raise HTTPException(
            status_code=403,
            detail=[NOT_AUTHORIZED],
        )

    @staticmethod
    def _sanitize_file_name(filename: str) -> str:
        return ospath.basename(filename.rstrip(ospath.sep))

    async def store(
        self,
        current_user_id: UserIDT,
        file: UploadFile,
        path: Optional[str] = None,
    ) -> str:
        """
        Add a file into current user's folder or subpath if a path is provided.
        TODO: Quotas
        """
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        file_name = self._sanitize_file_name(file.filename)
        assert ".." not in file_name, "Forbidden"
        if path is not None:
            path = self._can_use_dir_throw(path)
        logger.info("Adding '%s' ('%s') for '%s'", path, file_name, current_user.name)
        ret = await UserFilesDirectory(current_user_id).add_file(file_name, path, file)
        return ret

    def list(self, sub_path: str, current_user_id: UserIDT) -> DirectoryModel:
        """
        List the files in given subpath of the private folder.
        """
        # Leading / implies root directory
        _: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        sub_path = self._can_use_dir_throw(sub_path)
        folder = UserFilesDirectory(current_user_id)
        return self.list_and_format(folder, sub_path)

    @staticmethod
    def list_and_format(
        a_dir: Union[UserFilesDirectory, CommonFolder], sub_path: str
    ) -> DirectoryModel:
        assert ".." not in sub_path, "Not found"
        try:
            listing = a_dir.list(sub_path)
        except FileNotFoundError:
            # Prevent hammering on the endpoint
            time.sleep(0.5)
            assert False, "Not found"

        # Format data to return
        entries = [
            DirectoryEntryModel(name=a_name, type=a_type, size=a_size, mtime=a_mtime)
            for (a_name, a_type, a_size, a_mtime) in listing
        ]
        return DirectoryModel(path=sub_path, entries=entries)

    def create(self, source_path: str, current_user_id: UserIDT) -> str:
        """
        Create new file or folder
        """
        _: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # Leading / implies root directory
        dest_path = self._can_use_dir_throw(source_path, exclude_path=["/"])
        if not Path(dest_path).exists():
            folder = UserFilesDirectory(current_user_id)
            return folder.create(source_path)
        return ""

    def remove(self, source_path: str, current_user_id: UserIDT):
        """
        Remove a file or folder - return True if moved in trash , False if definitly deleted
        """
        # Leading / implies root directory
        _: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        source_path = self._can_use_dir_throw(source_path, exclude_path=["/"])
        folder = UserFilesDirectory(current_user_id)
        folder.remove(source_path)

    def move(self, source_path: str, dest_path: str, current_user_id: UserIDT) -> str:
        """
        Move - or rename - file or folder
        """
        # Leading / implies root directory
        _: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        source_path = self._can_use_dir_throw(source_path)
        dest_path = self._can_use_dir_throw(dest_path)
        folder = UserFilesDirectory(current_user_id)
        dest_path = folder.move(source_path, dest_path)
        return dest_path
