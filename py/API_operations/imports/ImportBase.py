# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import zipfile
from abc import ABC
from os.path import join
from typing import Union

from API_models.imports import ImportPrepReq, ImportRealReq, SimpleImportReq
from API_operations.helpers.TaskService import TaskServiceBase
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class ImportServiceBase(TaskServiceBase, ABC):
    """
        Common methods and data for import task steps.
    """
    req: Union[ImportPrepReq, ImportRealReq, SimpleImportReq]

    def __init__(self, prj_id: int, req: Union[ImportPrepReq, ImportRealReq, SimpleImportReq]):
        super().__init__(prj_id, req.task_id)
        # Received from parameters
        """ The project ID to import into """
        self.source_dir_or_zip: str = req.source_path
        """ The source file or directory """
        self.req = req
        # From legacy code, vault and temptask are in src directory
        self.vault = Vault(join(self.link_src, 'vault'))

    FROM_HTTP_FILE = "uploaded.zip"

    def manage_uploaded(self):
        # Special case, Http file was directly copied inside temp directory
        if self.source_dir_or_zip == self.FROM_HTTP_FILE:
            self.source_dir_or_zip = self.temp_for_task.in_base_dir_for(self.task_id, self.source_dir_or_zip)

    def unzip_if_needed(self):
        """
            If a .zip was sent, unzip it. Otherwise it is assumed that we point to an import directory.
        """
        if self.source_dir_or_zip.lower().endswith(".zip"):
            logger.info("SubTask : Unzip File into temporary folder")
            self.update_progress(1, "Unzip File into temporary folder")
            input_path = self.source_dir_or_zip
            self.source_dir_or_zip = self.temp_for_task.unzip_dir_for(self.task_id)
            with zipfile.ZipFile(input_path, 'r') as z:
                z.extractall(self.source_dir_or_zip)
