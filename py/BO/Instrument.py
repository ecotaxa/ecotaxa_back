# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Instruments, as of today just names i.e. instrument types.
#
from typing import List, Dict, Set

from DB import Session, Acquisition, Sample, Project
from DB.Project import ProjectIDListT, ProjectIDT
from DB.helpers.Direct import text
from DB.helpers.ORM import Query, any_
from helpers.DynamicLogs import get_logger

InstrumentIDT = str

logger = get_logger(__name__)


class DescribedInstrumentSet(object):
    """
        A list of instruments, with the projects referencing them.
    """

    def __init__(self, session: Session, project_ids: ProjectIDListT):
        qry: Query = session.query(Acquisition.instrument)
        qry = qry.join(Sample).join(Project)
        # TODO: WTF WTF just for adding a column to the select
        qry = qry.add_columns(text(Project.__table__.name + "." + Project.__table__.c.projid.name))
        # Below SQLAlchemy complains
        # qry = qry.add_columns(Project.projid)
        if len(project_ids) > 0:
            qry = qry.filter(Project.projid == any_(project_ids))
        qry = qry.distinct()
        instruments_by_proj: Dict[ProjectIDT, Set[InstrumentIDT]] = {}
        instrument_names = set()
        for ins_name, projid in qry.all():
            if ins_name:
                instruments_by_proj.setdefault(projid, set()).add(ins_name)
                instrument_names.add(ins_name)
            else:
                pass  # Filter NULL & empty strings
        self.by_project = instruments_by_proj
        self.instrument_names = sorted(list(instrument_names))

    def as_list(self) -> List[InstrumentIDT]:
        return self.instrument_names
