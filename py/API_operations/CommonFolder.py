# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Per-user or shared set of files.
#

from API_models.filesystem import DirectoryModel
from BO.Rights import RightsBO
from BO.User import UserIDT
from DB.User import User
from FS.CommonDir import CommonFolder
from API_operations.UserFilesFolder import UserFilesFolderService
from helpers.DynamicLogs import get_logger
from .helpers.Service import Service

logger = get_logger(__name__)


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
        _: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # Leading / implies root of user directory
        sub_path = sub_path.lstrip("/")
        folder = CommonFolder(self.config.common_folder())
        return UserFilesFolderService.list_and_format(folder, sub_path)
