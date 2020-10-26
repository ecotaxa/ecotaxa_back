# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import zipfile
from abc import ABC
from os.path import join

from API_operations.helpers.Service import Service
from BO.Project import ProjectIDListT
from DB import Task
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
        new_task = Task()
        new_task.taskclass = "TaskExportTxt"
        params = {"OutFile":"dwca.zip"}
        new_task.inputparam = json.dumps(params)
        self.session.add(new_task)
        self.session.flush()
        self.task_id = new_task.id
        # Get a temp directory
        self.temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        self.temp_dir = self.temp_for_task.base_dir_for(self.task_id)
        # Redirect logging
        log_file = self.temp_dir / 'ExportLogBack.txt'
        switch_log_to_file(str(log_file))
