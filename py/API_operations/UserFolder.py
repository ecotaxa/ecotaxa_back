# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Per-user set of files.
#

from fastapi import UploadFile

from BO.User import UserIDT
from DB import User
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
