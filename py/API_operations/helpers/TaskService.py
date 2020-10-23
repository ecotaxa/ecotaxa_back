# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from abc import ABC
from os.path import join
from typing import Optional

from DB.Project import Project
from DB.Task import Task
from FS.TempDirForTasks import TempDirForTasks
from helpers.DynamicLogs import get_logger, switch_log_to_file
from .Service import Service

logger = get_logger(__name__)


class TaskServiceBase(Service, ABC):
    """
        Common methods and data for asynchronous and long API_operations on a project.
    """
    prj_id: int = 0
    task_id: int = -1

    def __init__(self, prj_id: int, task_id: int):
        super().__init__()
        self.prj_id = prj_id
        self.task_id = task_id
        self.temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        # Redirect logging
        log_file = self.temp_for_task.base_dir_for(task_id) / 'TaskLogBack.txt'
        switch_log_to_file(str(log_file))
        # Work vars, load straight away
        prj = self.session.query(Project).get(prj_id)
        assert prj is not None
        self.prj = prj
        task = self.session.query(Task).get(task_id)
        # SimpleImport calls with no task during verification
        # assert task is not None
        self.task = task

    def update_task(self, taskstate: Optional[str], percent: Optional[int], message: str):
        """
            Update various fields in current task.
        """
        if taskstate is not None:
            self.task.taskstate = taskstate
        if percent is not None:
            self.task.progresspct = percent
        self.task.progressmsg = message
        self.task.lastupdate = datetime.datetime.now()
        self.session.commit()

    def update_progress(self, percent: int, message: str):
        self.update_task(taskstate=None, percent=percent, message=message)

    def report_progress(self, current, total):
        self.update_progress(20 + 80 * current / total,
                             "Processing files %d/%d" % (current, total))
