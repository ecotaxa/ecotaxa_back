# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import shutil
from os.path import join

from db.Task import Task
from framework.Service import Service
from fs.TempDirForTasks import TempDirForTasks


class TaskService(Service):
    """
        Basic CRUD operations on Task
    """

    def create(self) -> int:
        tsk = Task()
        self.session.add(tsk)
        self.session.commit()
        # Wipe any directory, which belongs to another task with same ID
        temp_for_task = TempDirForTasks(join(self.link_src, 'temptask')).base_dir_for(tsk.id)
        shutil.rmtree(temp_for_task)
        return tsk.id
