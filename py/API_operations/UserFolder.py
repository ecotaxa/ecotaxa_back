# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Per-user or shared set of files.
#
import os
import time
from typing import Optional, Union

from fastapi import UploadFile

from API_models.filesystem import DirectoryEntryModel, DirectoryModel
from BO.Rights import RightsBO
from BO.User import UserIDT
from DB.User import User
from FS.CommonDir import CommonFolder
from FS.UserDir import UserDirectory
from helpers.DynamicLogs import get_logger
from .helpers.Service import Service

logger = get_logger(__name__)


class UserFolderService(Service):
    """
    A service for storing/cleaning user specific folders.
    """

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _sanitize_filename_throw(filename: str) -> str:
        assert ".." not in filename, "Forbidden"
        return os.path.basename(filename.rstrip(os.path.sep))

    @staticmethod
    def _sanitize_path_throw(path: str) -> str:
        assert ".." not in path, "Forbidden"
        return path.lstrip(os.path.sep)

    @staticmethod
    def _sanitize_tag_throw(tag: str) -> str:
        assert ".." not in tag, "Forbidden"
        assert os.path.sep not in tag, "Forbidden"
        return tag

    async def store(
        self,
        current_user_id: UserIDT,
        file: UploadFile,
        path: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> str:
        """
        Add a file into current user's folder. If a tag is provided, then all files
        with the same tag are grouped (in a sub-directory). Otherwise, a temp directory
        with only this file will be created.
        TODO: Quotas
        """
        file_name = self._sanitize_filename_throw(file.filename)
        if path is not None:
            path = self._sanitize_path_throw(path)
        if tag is not None:
            tag = self._sanitize_tag_throw(tag)
        # current_user = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # assert current_user is not None
        logger.info(
            "Adding '%s' ('%s'/'%s') for '%s'", tag, path, file_name, current_user.name
        )
        ret = await UserDirectory(current_user_id, tag).add_file(file_name, path, file)
        return ret

    def list(self, sub_path: str, current_user_id: UserIDT) -> DirectoryModel:
        """
        List the files in given subpath of the private folder.
        """
        # Leading / implies root directory
        sub_path = sub_path.lstrip("/")
        # current_user = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # assert current_user is not None, "Not authorized"
        folder = UserDirectory(current_user_id, None)
        return self.list_and_format(folder, sub_path)

    @staticmethod
    def list_and_format(
        a_dir: Union[UserDirectory, CommonFolder], sub_path: str
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


class CommonFolderService(Service):
    """
    A service for navigating in specific shared folder.
    """

    def __init__(self) -> None:
        super().__init__()

    def list(self, sub_path: str, current_user_id: UserIDT) -> DirectoryModel:
        """
        List the files in given subpath of the common folder.
        """
        # current_user = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # assert current_user is not None, "Not authorized"
        # Leading / implies root of user directory
        sub_path = sub_path.lstrip("/")
        folder = CommonFolder(self.config.common_folder())
        return UserFolderService.list_and_format(folder, sub_path)
