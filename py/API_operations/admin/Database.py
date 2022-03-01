# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A service for direct DB access.
#
from typing import Tuple, List

from API_operations.helpers.Service import Service
from BO.Rights import RightsBO
from BO.User import UserIDT
from DB.User import Role
from DB.helpers.Direct import text
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class DatabaseService(Service):
    """
        Admin part of ML in EcoTaxa.
    """

    def __init__(self) -> None:
        super().__init__()

    def execute_query(self, current_user_id: UserIDT,
                      query: str) -> Tuple[List[str], List[List]]:
        # Security barrier
        _user = RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        # Pick the read-only session for safety
        res = self.ro_session.execute(text(query))
        header = [a_col for a_col in res.keys()]
        values = [list(a_val) for a_val in res]
        return header, values
