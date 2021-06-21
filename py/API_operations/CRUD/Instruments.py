# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

from BO.Instrument import DescribedInstrumentSet, InstrumentIDT
from DB.Project import ProjectIDListT
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service

logger = get_logger(__name__)


class InstrumentsService(Service):
    """
        Basic CRUD operation on instrument
    """

    def query(self, project_ids: ProjectIDListT) -> List[InstrumentIDT]:
        ret = DescribedInstrumentSet(self.session, project_ids).as_list()
        return ret
