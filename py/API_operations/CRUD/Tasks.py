# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import shutil
from io import StringIO
from os.path import join
from typing import IO, Tuple

from BO.Rights import NOT_FOUND, NOT_AUTHORIZED
from BO.User import UserIDT
from DB import User, Role
from DB.Task import Task
from FS.TempDirForTasks import TempDirForTasks
from ..helpers.Service import Service


class TaskService(Service):
    """
        Basic CRUD API operations on Tasks
    """

    def create(self) -> int:
        tsk = Task()
        self.session.add(tsk)
        self.session.commit()
        # Wipe any directory, which belongs to another task with same ID
        temp_for_task = TempDirForTasks(join(self.link_src, 'temptask')).base_dir_for(tsk.id)
        shutil.rmtree(temp_for_task)
        return tsk.id

    def get_temp(self, task_id: int, inside: str) -> str:
        temp_for_task = TempDirForTasks(join(self.link_src, 'temptask')).in_base_dir_for(task_id, inside)
        return temp_for_task

    def get_file_stream(self, current_user_id: UserIDT, task_id: int) -> Tuple[IO, str]:
        """
            Return a stream containing the file associated with this task.
        """
        # Sanity & security checks
        task: Task = self.session.query(Task).get(task_id)
        assert task is not None, NOT_FOUND
        current_user = self.session.query(User).get(current_user_id)
        assert (task.owner_id == current_user_id) or (current_user.has_role(Role.APP_ADMINISTRATOR)), NOT_AUTHORIZED
        # TODO: 'temptask' constant is repeated in many places
        temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        temp_dir = temp_for_task.base_dir_for(task_id)
        assert task.inputparam is not None
        params = json.loads(task.inputparam)
        out_file_name = params["OutFile"]
        out_file_path = temp_dir / out_file_name
        try:
            return open(out_file_path, mode="rb"), out_file_name
        except IOError:  # pragma:nocover
            return StringIO("NOT FOUND"), out_file_name
