# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A service dedicated to checking that a change was successfully propagated to a secondary user or DB
#
import time

from API_operations.helpers.Service import Service
from DB.helpers.Core import select
from DB.helpers.ORM import Session, Table, ModelT, text
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class DBSyncService(Service):
    """
    The service takes DB row(s) (on master) and then enables to wait
        until the slave (read-only) has the same row(s).
    """

    def __init__(self, a_table: ModelT, *args):
        super().__init__()
        table: Table = a_table.__table__
        self.table_name = table.name
        qry = select([text("%s.*" % table.name)])
        for a_col, a_val in zip(args[::2], args[1::2]):
            qry = qry.where(a_col == a_val)
        self.qry = qry
        self.ref_val = self._get_result(self.session)

    MAX_WAIT = 2  # 2 seconds is quite a lot

    def _get_result(self, session: Session):
        res = session.execute(self.qry)
        ret = [tuple(a_row) for a_row in res]
        return set(ret)

    def wait(self) -> None:
        start_time = time.time()
        # Wait MAX_WAIT max for the sync
        waited: float = 0
        while waited < self.MAX_WAIT:
            new_val = self._get_result(self.ro_session)
            if new_val == self.ref_val:
                logger.info("Sync of %s in %.3fs", self.table_name, waited)
                return
            time.sleep(0.1)
            waited = time.time() - start_time
        logger.warning("NO SYNC of %s in %.3fs", self.table_name, waited)
