# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A service dedicated to checking that a change was successfully propagated to a secondary user or DB
#
import time

from sqlalchemy.sql import select

from helpers.DynamicLogs import get_logger

from API_operations.helpers.Service import Service
from DB.helpers.ORM import Model, Query, Table, ModelT, text

logger = get_logger(__name__)


class DBSyncService(Service):
    """
        The service takes a slave DB row CTID and then enables to wait
           until the CTID changes, which will most likely
           be provoked by an update, i.e. a row movement.
    """

    def __init__(self, a_table: ModelT, *args):
        super().__init__()
        table: Table = a_table.__table__
        self.table_name = table.name
        qry = select([text("%s.ctid" % table.name)])  # type:ignore
        for a_col, a_val in zip(args[::2], args[1::2]):
            qry = qry.where(a_col == a_val)
        self.qry = qry
        self.ref_ctid = list(self.ro_session.execute(qry))

    MAX_WAIT = 2

    def wait(self):
        start_time = time.time()
        # Wait half a second max for the sync
        waited = 0
        while waited < self.MAX_WAIT:
            new_ctid = list(self.ro_session.execute(self.qry))
            if new_ctid != self.ref_ctid:
                logger.info("Sync of %s in %.3fs", self.table_name, waited)
                return
            time.sleep(0.1)
            waited = time.time() - start_time
        logger.warning("NO SYNC of %s in %.3fs", self.table_name, waited)
