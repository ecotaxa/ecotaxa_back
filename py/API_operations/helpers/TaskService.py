# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from abc import ABC
from os.path import join
from typing import Union, Optional

from DB.Project import Project
from DB.Task import Task
from FS.TempDirForTasks import TempDirForTasks
from helpers.DynamicLogs import get_logger, switch_log_to_file
from .Service import Service

logger = get_logger(__name__)


class TaskServiceBase(Service, ABC):
    """
        Common methods and data for API_operations on a project.
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
        # Work vars
        self.prj: Union[Project, None] = None
        self.task: Union[Task, None] = None

    def prepare_run(self):
        """
            Load what's needed for run.
        """
        self.prj = self.session.query(Project).filter_by(projid=self.prj_id).first()
        assert self.prj is not None
        self.task = self.session.query(Task).filter_by(id=self.task_id).first()
        assert self.task is not None

    def update_task(self, taskstate: Optional[str], percent: Optional[int], message: str):
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
