# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# An enumerated set of Process(es)
#
from typing import List

from API_models.crud import ColUpdateList
from BO.Project import ProjectIDListT
from BO.helpers.MappedTable import MappedTable
from DB import Session, Query, Project, Process
from DB.helpers.ORM import any_, contains_eager
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

ProcessIDListT = List[int]  # Typings, to be clear that these are not e.g. project IDs

logger = get_logger(__name__)


class EnumeratedProcessSet(MappedTable):
    """
        A list of process-es, known by their IDs.
    """

    def __init__(self, session: Session, ids: ProcessIDListT):
        super().__init__(session)
        self.ids = ids

    def get_projects_ids(self) -> ProjectIDListT:
        """
            Return the project IDs for the held process IDs.
        """
        qry: Query = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Project.all_processes)
        qry = qry.filter(Process.processid == any_(self.ids))
        with CodeTimer("Prjs for %d processes: " % len(self.ids), logger):
            return [an_id for an_id in qry.all()]

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
            Apply all updates on all processes pointed at by the list.
        """
        return self._apply_on_all(Process, project, updates)

    def add_filter(self, upd):
        return upd.filter(Process.processid == any_(self.ids))