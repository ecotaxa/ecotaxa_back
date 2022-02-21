# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#

from API_models.constants import Constants
from DB.helpers.Postgres import text
from ..helpers.Service import Service


class ConstantsService(Service):
    """
        App uptime constants.
    """

    def get(self) -> Constants:
        ret = Constants()
        conf_keys = set(self.config.list_cnf())
        if 'APPMANAGER_EMAIL' in conf_keys and 'APPMANAGER_NAME' in conf_keys:
            ret.app_manager = [self.config.get_cnf('APPMANAGER_NAME'),
                               self.config.get_cnf('APPMANAGER_EMAIL')]
        ret.countries = [a_country for (a_country,) in self.session.query(text('countryname from countrylist'))]
        return ret
