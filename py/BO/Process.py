# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# An enumerated set of Process(es)
#
from typing import List, ClassVar

from BO.ColumnUpdate import ColUpdateList
from BO.helpers.MappedEntity import MappedEntity
from BO.helpers.MappedTable import MappedTable
from DB import Session, Process, Sample
from DB.Project import ProjectIDListT, Project
from DB.helpers.ORM import any_
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

ProcessIDT = int
ProcessIDListT = List[int]  # Typings, to be clear that these are not e.g. project IDs
ProcessOrigIDT = str

logger = get_logger(__name__)


def _get_proj(prc: Process):
    return prc.acquisition.sample.project


class ProcessBO(MappedEntity):
    """
    A processing, which is _how_ collected [sub]samples were treated to give images.
    """

    FREE_COLUMNS_ATTRIBUTE: ClassVar = "process"
    PROJECT_ACCESSOR: ClassVar = _get_proj
    MAPPING_IN_PROJECT: ClassVar = "process_mappings"

    def __init__(self, session: Session, process_id: ProcessIDT):
        super().__init__(session)
        self.process = session.query(Process).get(process_id)

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a Sample field somehow then return it"""
        return getattr(self.process, item)


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
        qry = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Project.all_samples)
        qry = qry.join(Sample.all_acquisitions)
        qry = qry.join(Process)
        qry = qry.filter(Process.processid == any_(self.ids))
        with CodeTimer("Prjs for %d processes: " % len(self.ids), logger):
            return [an_id for an_id, in qry]

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
        Apply all updates on all processes pointed at by the list.
        """
        return self._apply_on_all(Process, project, updates.lst)

    def add_filter(self, upd):
        return upd.filter(Process.processid == any_(self.ids))
