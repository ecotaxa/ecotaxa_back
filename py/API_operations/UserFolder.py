# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Per-user or shared set of files.
#
import time

from fastapi import UploadFile

from API_models.filesystem import DirectoryEntryModel, DirectoryModel
from BO.User import UserIDT
from DB import User
from FS.CommonDir import CommonFolder
from FS.UserDir import UserDirectory
from helpers.DynamicLogs import get_logger
from .helpers.Service import Service

logger = get_logger(__name__)


class UserFolderService(Service):
    """
        A service for storing/cleaning user specific folders.
    """

    def __init__(self):
        super().__init__()

    async def store(self, current_user_id: UserIDT, file: UploadFile) -> str:
        """
            Add a file into current user's folder.
            TODO: Quotas
        """
        file_name = file.filename
        current_user = self.ro_session.query(User).get(current_user_id)
        assert current_user is not None
        logger.info("Adding '%s' for '%s'", file_name, current_user.name)
        ret = await UserDirectory(current_user_id).add_file(file_name, file)
        return ret


class CommonFolderService(Service):
    """
        A service for navigating in specific shared folder.
    """

    def __init__(self):
        super().__init__()

    async def list(self, sub_path: str, current_user_id: UserIDT) -> DirectoryModel:
        """
            List the files in given subpath of the common folder.
        """
        current_user = self.ro_session.query(User).get(current_user_id)
        assert current_user is not None, "Not authorized"
        folder = CommonFolder(self.config)

        try:
            assert "../" not in sub_path, "Not found"
            listing = folder.list(sub_path)
        except FileNotFoundError:
            # Prevent hammering on the endpoint
            time.sleep(0.5)
            assert False, "Not found"

        # Format data to return
        entries = [DirectoryEntryModel(name=a_name, type=a_type, size=a_size, mtime=a_mtime)
                   for (a_name, a_type, a_size, a_mtime) in listing]
        return DirectoryModel(path=sub_path, entries=entries)
