# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Instruments, as of today just names i.e. instrument types.
#
from typing import List

from BO.Project import ProjectIDListT
from DB import Session, Acquisition, Sample, Project
from DB.helpers.ORM import Query
from helpers.DynamicLogs import get_logger

InstrumentIDT = str

logger = get_logger(__name__)


class DescribedInstrumentSet(object):
    """
        A list of instruments.
    """

    def __init__(self, session: Session, project_ids: ProjectIDListT):
        self.instrument_names: List[InstrumentIDT] = []
        qry: Query = session.query(Acquisition.instrument).distinct()
        qry = qry.join(Sample).join(Project)
        if len(project_ids) > 0:
            qry = qry.filter(Project.projid.in_(project_ids))
        qry = qry.order_by(Acquisition.instrument)
        self.instrument_names = [nm for nm, in qry.all()
                                 if nm]  # Filter NULL & empty strings

    def as_list(self) -> List[InstrumentIDT]:
        return self.instrument_names
