# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, List, Optional

from BO.Instrument import DescribedInstrumentSet, InstrumentIDT
from DB.Instrument import Instrument
from DB.Project import ProjectIDListT
from FS.MachineLearningModels import SavedModels
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service

logger = get_logger(__name__)


class InstrumentsService(Service):
    """
    Basic CRUD operation on instrument
    """

    def query(self, project_ids: Optional[ProjectIDListT]) -> List[InstrumentIDT]:
        if project_ids is None:
            qry = self.ro_session.query(Instrument.instrument_id)
            qry = qry.order_by(Instrument.instrument_id)
            return [an_id for an_id, in qry]
        else:
            ret = DescribedInstrumentSet(self.session, project_ids).as_list()
        return ret

    def cnn_networks(
        self, instrument: Optional[InstrumentIDT]
    ) -> Dict[InstrumentIDT, List[str]]:
        """
        Available CNN networks per instrument, all instruments or only the given one.
        """
        qry = self.ro_session.query(Instrument.instrument_id)
        if instrument is not None:
            qry = qry.filter(Instrument.instrument_id == instrument)
        instrument_ids = [an_id for an_id, in qry.order_by(Instrument.instrument_id)]
        networks = sorted(SavedModels(self.config).list(), key=str.lower)
        ret = {}
        for an_id in instrument_ids:
            for_instrument = [
                a_network
                for a_network in networks
                if SavedModels.is_for_instrument(a_network, an_id)
            ]
            if for_instrument or instrument is not None:
                ret[an_id] = for_instrument
        return ret
