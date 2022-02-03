# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#

from API_models.constants import Constants
from ..helpers.Service import Service
from DB.helpers.Postgres import text

class ConstantsService(Service):
    """
        App uptime constants.
    """

    def get(self) -> Constants:
        ret = Constants()
        if 'APPMANAGER_EMAIL' in self.config and 'APPMANAGER_NAME' in self.config:
            ret.app_manager = [self.config['APPMANAGER_NAME'], self.config['APPMANAGER_EMAIL']]
        ret.countries = [a_country for (a_country,) in self.session.query(text('countryname from countrylist'))]
        return ret
