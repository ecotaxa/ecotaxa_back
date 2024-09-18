# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os
import zipfile
from abc import ABC
from typing import Union

from API_models.imports import ImportReq, SimpleImportReq
from API_operations.helpers.JobService import JobServiceOnProjectBase, ArgsDict
from BO.User import UserIDT
from FS.CommonDir import CommonFolder
from FS.UserDir import UserDirectory
from FS.UserFilesDir import UserFilesDirectory
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class ImportServiceBase(JobServiceOnProjectBase, ABC):
    """
    Common methods and data for import task steps.
    """

    req: Union[ImportReq, SimpleImportReq]

    def __init__(self, prj_id: int, req: Union[ImportReq, SimpleImportReq]):
        super().__init__(prj_id)
        """ The project ID to import into """
        self.req = req
        # From legacy code, vault and temptask are in src directory
        self.vault = Vault(self.config.vault_dir())

    def init_args(self, args: ArgsDict) -> ArgsDict:
        super().init_args(args)
        args["req"] = self.req.dict()
        return args

    def unzip_if_needed(self, owner_id: UserIDT) -> str:
        """
        If a .zip was sent, unzip it. Otherwise it is assumed that we point to an import directory.
        """
        source_dir_or_zip = self.req.source_path
        my_files_source_dir = UserFilesDirectory(owner_id)._root_path.joinpath(
            source_dir_or_zip.lstrip(os.path.sep)
        )
        if my_files_source_dir.exists():

            return my_files_source_dir
        elif UserDirectory(owner_id).contains(source_dir_or_zip):
            # OK
            pass
        else:
            # prevent directory escape trick
            assert ".." not in source_dir_or_zip
            source_dir_or_zip = CommonFolder(self.config.common_folder()).path_to(
                source_dir_or_zip
            )
        if source_dir_or_zip.lower().endswith(".zip"):
            logger.info("SubTask : Unzip File into temporary folder")
            self.update_progress(1, "Unzip File into temporary folder")
            input_path = source_dir_or_zip
            assert self.job_id
            source_dir_or_zip = self.temp_for_jobs.unzipped_dir_for(self.job_id)
            with zipfile.ZipFile(input_path, "r") as z:
                z.extractall(source_dir_or_zip)
        return source_dir_or_zip
