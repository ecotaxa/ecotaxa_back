# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import zipfile
from abc import ABC
from os.path import join

from API_operations.CRUD.Tasks import TaskService
from API_operations.helpers.Service import Service
from BO.Project import ProjectIDListT
from FS.TempDirForTasks import TempDirForTasks
from helpers.DynamicLogs import get_logger, switch_log_to_file

logger = get_logger(__name__)


class ExportServiceBase(Service, ABC):
    """
        Common methods and data for export.
        It's not really needed to have a task, but we must have some disk space for the result.
    """
    def __init__(self, prj_ids: ProjectIDListT):
        super().__init__()
        self.project_ids = prj_ids
        self.task_id = TaskService().create()
        # Get a temp directory
        self.temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        self.temp_dir = self.temp_for_task.base_dir_for(self.task_id)
        # Redirect logging
        log_file = self.temp_dir / 'ExportLogBack.txt'
        switch_log_to_file(str(log_file))

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
