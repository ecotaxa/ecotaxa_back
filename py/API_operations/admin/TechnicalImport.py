# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Technical PG dump-like import of a single project.
#
import os
from typing import Any, Dict

from fastapi import HTTPException
from starlette import status

from API_operations.helpers.Service import Service
from BO.Rights import RightsBO
from BO.technical.TechImport import TechnicalImport
from DB.User import Role, UserIDT
from FS.UserFilesDir import UserFilesDirectory
from helpers.DynamicLogs import get_logger
from helpers.httpexception import DETAIL_EXTRACTION_IN_PROGRESS

logger = get_logger(__name__)


class TechnicalImportService(Service):
    """
    Admin service restoring a single-project technical archive (.tar, .tar.zst, or directory)
    located in the current user's directory.
    """

    def run(self, current_user_id: UserIDT, archive_name: str) -> Dict[str, Any]:
        RightsBO.user_has_role(
            self.ro_session, current_user_id, Role.APP_ADMINISTRATOR
        )
        user_dir = UserFilesDirectory(current_user_id)
        if user_dir.has_extraction_in_progress(archive_name):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=DETAIL_EXTRACTION_IN_PROGRESS,
            )

        root = user_dir._root_path.resolve()
        rel = archive_name.lstrip(os.path.sep)
        if not rel:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Empty archive name",
            )
        candidate = (root / rel).resolve()
        if candidate == root or root not in candidate.parents:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid archive path",
            )
        if not candidate.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Archive not found: {archive_name}",
            )

        importer = TechnicalImport(self.session, self.config.vault_dir())
        return importer.import_project(candidate)
