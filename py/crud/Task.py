# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from db.Task import Task
from framework.Service import Service


class TaskService(Service):
    """
        Basic CRUD operations on Project
    """

    def create(self) -> int:
        tsk = Task()
        self.session.add(tsk)
        self.session.commit()
        return tsk.id
