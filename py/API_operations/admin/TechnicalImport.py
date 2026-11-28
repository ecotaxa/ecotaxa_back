# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Technical PG dump-like import of a single project.
#
import os
import tarfile
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from starlette import status

from API_operations.helpers.JobService import ArgsDict, JobServiceBase
from BO.Rights import RightsBO
from BO.technical.TechImport import TechnicalImport
from DB.Job import JobIDT
from DB.User import Role, UserIDT
from FS.UserFilesDir import UserFilesDirectory
from helpers.CustomException import UnprocessableEntityException
from helpers.DynamicLogs import LogsSwitcher, get_logger
from helpers.httpexception import DETAIL_EXTRACTION_IN_PROGRESS

logger = get_logger(__name__)


class TechnicalImportService(JobServiceBase):
    """
    Job service restoring a single-project technical archive (.tar.zst)
    located in the current user's directory.
    """

    JOB_TYPE = "TechnicalImport"

    def __init__(
        self,
        archive_name: str,
        target_project_id: Optional[int] = None,
        owner_id: Optional[UserIDT] = None,
    ) -> None:
        super().__init__()
        self.archive_name: str = archive_name
        self.target_project_id: Optional[int] = target_project_id
        self.owner_id: Optional[UserIDT] = owner_id

    def init_args(self, args: ArgsDict) -> ArgsDict:
        args["archive_name"] = self.archive_name
        args["target_project_id"] = self.target_project_id
        args["owner_id"] = self.owner_id
        return args

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        json_args["archive_name"] = str(json_args["archive_name"])
        if json_args.get("target_project_id") is not None:
            json_args["target_project_id"] = int(json_args["target_project_id"])
        if json_args.get("owner_id") is not None:
            json_args["owner_id"] = int(json_args["owner_id"])

    def _resolve_archive_path(self, user_id: UserIDT) -> Path:
        user_dir = UserFilesDirectory(user_id)
        if user_dir.has_extraction_in_progress(self.archive_name):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=DETAIL_EXTRACTION_IN_PROGRESS,
            )

        root = user_dir._root_path.resolve()
        rel = self.archive_name.lstrip(os.path.sep)
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
                detail=f"Archive not found: {self.archive_name}",
            )
        return candidate

    def run(self, current_user_id: UserIDT) -> JobIDT:
        RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        if not self.config.get_enable_tech_import():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Technical import is disabled.",
            )
        if self.target_project_id is not None and self.target_project_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid target_project_id: {self.target_project_id}",
            )
        self.owner_id = current_user_id
        self._resolve_archive_path(current_user_id)
        self.create_job(self.JOB_TYPE, current_user_id)
        return self.job_id

    def do_background(self) -> None:
        with LogsSwitcher(self):
            self.do_import()

    def do_import(self) -> None:
        owner_id = (
            self.owner_id if self.owner_id is not None else self._get_job().owner_id
        )
        try:
            candidate = self._resolve_archive_path(owner_id)
        except HTTPException as e:
            err_msg = str(e.detail)
            logger.error("Technical import failed: %s", err_msg)
            self.set_job_result(errors=[err_msg], infos={})
            return

        logger.info("Importing technical archive %s", candidate)
        self.update_progress(1, "Starting TechnicalImport")
        importer = TechnicalImport(self.config.vault_dir())
        try:
            summary = importer.import_project(
                candidate,
                progress_start=1,
                progress_end=99,
                progress_cb=self.update_progress,
                target_project_id=self.target_project_id,
            )
        except (UnprocessableEntityException, tarfile.TarError, OSError) as e:
            self.session.rollback()
            err_msg = (
                e.message if isinstance(e, UnprocessableEntityException) else str(e)
            )
            logger.error("Technical import failed: %s", err_msg)
            self.set_job_result(errors=[err_msg], infos={})
            return

        self.update_progress(100, "Import successful")
        self.set_job_result(errors=[], infos=summary)
