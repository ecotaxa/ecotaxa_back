# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Instruments, as of today just names i.e. instrument types.
#
from typing import List, Dict

from DB import Session
from DB.Instrument import InstrumentIDT
from DB.Project import ProjectIDListT, ProjectIDT, Project
from DB.helpers.ORM import any_
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class DescribedInstrumentSet(object):
    """
    A list of (project ids, instruments ids)
    """

    def __init__(self, session: Session, project_ids: ProjectIDListT):
        qry = session.query(Project.projid, Project.instrument_id)
        qry = qry.filter(Project.projid == any_(project_ids))
        instruments_by_proj: Dict[ProjectIDT, InstrumentIDT] = {}
        for projid, ins_id in qry:
            instruments_by_proj[projid] = ins_id
        self.by_project = instruments_by_proj

    def as_list(self) -> List[InstrumentIDT]:
        ids = set(self.by_project.values())
        return sorted(ids)
