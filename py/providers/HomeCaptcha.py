# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Client for CAPTCHA verification (Google reCAPTCHA or internal EcoTaxa service).
#
from typing import Optional, List

import requests
from fastapi import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT, HTTP_401_UNAUTHORIZED

from helpers.AppConfig import Config

RECAPTCHA_API_SITEVERIFY = "https://www.google.com/recaptcha/api/siteverify"


class HomeCaptcha(object):
    """ """

    def __init__(self, homecaptcha_secret: str):
        self.secret = homecaptcha_secret

        config = Config()
        self.recaptchaid = config.get_recaptchaid() or ""
        self.all_in_one = config.get_all_in_one() == "on"
        if self.recaptchaid != "":
            recaptchasecret = config.get_recaptchasecret() or ""
            if recaptchasecret != "":
                self.secret = recaptchasecret
        self.max_token_length = config.get_max_captcha_token_length()

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
            url_captcha = RECAPTCHA_API_SITEVERIFY

        elif self.all_in_one:
            return None
        else:
            params = {
                "r": response,
            }

            url_captcha = Config().get_account_validation_url() + str(
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
                if len(a_str) >= self.max_token_length:
                    detail = ["invalid no_bot reason 2"]
        if detail != []:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail=detail,
            )
        remote_ip = no_bot[0]
        response = no_bot[1]

        error = self.validate(remote_ip, response)
        if error is not None:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=[error])
