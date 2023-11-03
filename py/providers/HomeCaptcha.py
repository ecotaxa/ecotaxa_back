# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Clients to Google API services, so far just one.
#
from typing import Optional, List
from fastapi import HTTPException
from helpers.AppConfig import Config
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_401_UNAUTHORIZED
import requests


class HomeCaptcha(object):
    """ """

    def __init__(self, captcha_secret: str):
        self.secret = captcha_secret

    def validate(self, remote_ip: str, response: str) -> Optional[str]:
        """
            Call the API verification endpoint
        :return: None if OK, otherwise string with error.
        """
        params = {
            "r": response,
        }
        # @see https://developers.google.com/recaptcha/docs/verify
        url_captcha = str(Config().get_account_request_url() or "") + str(
            "gui/checkcaptcha"
        )
        rsp = requests.request("GET", url=url_captcha, params=params)

        if rsp.status_code != 200 or not rsp.json()["success"]:
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
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        remote_ip = no_bot[0]
        response = no_bot[1]
        error = self.validate(remote_ip, response)
        if error is not None:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=[error])
