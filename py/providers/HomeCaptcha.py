# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Clients to Google API services, so far just one.
#
from typing import Optional, List

import requests
from fastapi import HTTPException

from helpers.AppConfig import Config


class HomeCaptcha(object):
    """ """

    def __init__(self, homecaptcha_secret: str):
        self.secret = homecaptcha_secret

        config = Config()
        self.recaptchaid = str(config.get_recaptchaid() or "")
        if self.recaptchaid != "":
            recaptchasecret = str(config.get_recaptchasecret() or "")
            if recaptchasecret != "":
                self.secret = recaptchasecret

    def _daily_get_iplist(self):
        # no usage now
        return

    def validate(self, remote_ip: str, response: str) -> Optional[str]:
        """
        Call the API verification endpoint
        :return: None if OK, otherwise string with error.
        """
        if self.recaptchaid != "":
            # call google captcha
            # @see https://developers.google.com/recaptcha/docs/verify
            params = {
                "response": response,
                "secret": self.secret,
                "remoteip": remote_ip,
            }
            url_captcha = "https://www.google.com/recaptcha/api/siteverify"

        else:
            params = {
                "r": response,
            }

            url_captcha = str(Config().get_account_request_url() or "") + str(
                "gui/checkcaptcha"
            )
        rsp = requests.request("GET", url=url_captcha, params=params)
        rspjson = rsp.json()
        if (
            int(rsp.status_code) != 200
            or "success" not in rspjson
            or not rspjson["success"]
        ):
            return rsp.text.replace("\n", "")
        return None

    def verify_captcha(self, no_bot: Optional[List[str]]) -> None:
        """
        get captcha as a list and format to call validate
        :return: None if OK, otherwise HTTPException.
        """
        detail = []
        no_bot = list(no_bot or ["", ""])
        if no_bot == ["", ""]:
            detail = ["reCaptcha verif needs data"]
        elif len(no_bot) != 2:
            detail = ["invalid no_bot reason 1"]
        else:
            for a_str in no_bot:
                if len(a_str) >= 1024:
                    detail = ["invalid no_bot reason 2"]
        if detail != []:
            raise HTTPException(
                status_code=422,
                detail=detail,
            )
        remote_ip = no_bot[0]
        response = no_bot[1]

        error = self.validate(remote_ip, response)
        if error is not None:
            raise HTTPException(status_code=401, detail=[error])
