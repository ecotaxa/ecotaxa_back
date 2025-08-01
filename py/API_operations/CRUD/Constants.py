# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from BO.DataLicense import AccessLevelEnum
from API_models.constants import Constants, FORMULAE
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
        ret.account_validation = self.config.get_account_validation() == "on"
        ret.email_verification = self.config.get_user_email_verification() == "on"
        ret.recaptchaid = self.config.get_recaptchaid() != None
        ret.formulae = FORMULAE
        ret.default_project_access = AccessLevelEnum.PUBLIC
        ret.max_upload_size = self.config.get_max_upload_size()
        ret.time_to_live = self.config.get_time_to_live()

        return ret
