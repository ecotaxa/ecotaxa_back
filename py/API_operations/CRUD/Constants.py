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
        app_manager = self.config.get_app_manager()
        if all(app_manager):
            ret.app_manager = list(app_manager)  # type:ignore # mypy doesn't know all()
        ret.countries = [
            a_country
            for (a_country,) in self.session.query(text("countryname from countrylist"))
        ]
        return ret
