# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Clients to Google API services, so far just one.
#
from typing import Optional

import requests


class ReCAPTCHAClient(object):
    """ """

    API_ENDPOINT = "https://www.google.com/recaptcha/api/siteverify"

    def __init__(self, captcha_id: str, captcha_secret: str):
        self.id_ = captcha_id
        self.secret = captcha_secret

    def validate(self, remote_ip: str, response: str) -> Optional[str]:
        """
            Call the API verification endpoint
        :return: None if OK, otherwise string with error.
        """
        api_params = {
            "response": response,
            "secret": self.secret,
            "remoteip": remote_ip,
        }
        # @see https://developers.google.com/recaptcha/docs/verify
        rsp = requests.request("GET", url=self.API_ENDPOINT, params=api_params)
        if rsp.status_code != 200 or not rsp.json()["success"]:
            return rsp.text.replace("\n", "")
        return None
