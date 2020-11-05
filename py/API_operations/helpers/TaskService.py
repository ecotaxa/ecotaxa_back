# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
import json
from abc import ABC
from os.path import join
from typing import Optional

from BO.User import UserIDT
from DB.Project import Project
from DB.Task import Task
from FS.TempDirForTasks import TempDirForTasks
from helpers.DynamicLogs import get_logger, switch_log_to_file
from .Service import Service

logger = get_logger(__name__)


class TaskServiceBase(Service, ABC):
    """
        Common methods and data for asynchronous and long operations.
    """
    task_id: int = -1

    def __init__(self, task_id: Optional[int] = None, task_type: Optional[str] = None):
        super().__init__()
        if task_id is None:
            # Create a new task
            task = Task()
            task.taskclass = task_type
            self.session.add(task)
            self.session.flush()
        else:
            # Fetch existing task
            task = self.session.query(Task).get(task_id)
            # SimpleImport calls with no task during verification
            # assert task is not None
        self.task = task
        self.task_id = task.id
        self.temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        # Redirect logging
        log_file = self.temp_for_task.base_dir_for(self.task_id) / 'TaskLogBack.txt'
        switch_log_to_file(str(log_file))

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

    def set_task_params(self, owner_id: UserIDT, file_name: str):
        """
            Set export task features for this export.
        """
        task = self.session.query(Task).get(self.task_id)
        assert task is not None
        params = {"OutFile": file_name}
        task.inputparam = json.dumps(params)
        task.owner_id = owner_id
        self.session.commit()


class TaskServiceOnProjectBase(TaskServiceBase, ABC):
    """
        Common data for asynchronous and long operations, on a project.
    """
    prj_id: int = 0

    def __init__(self, prj_id: int, task_id: int):
        super().__init__(task_id)
        self.prj_id = prj_id
        # Work vars, load straight away
        prj = self.session.query(Project).get(prj_id)
        assert prj is not None
        self.prj = prj
