# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Clients to Google API services, so far just one.
#
from typing import Optional, List
from fastapi import HTTPException
from helpers.AppConfig import Config
import requests
from BO.Rights import NOT_AUTHORIZED


class HomeCaptcha(object):
    """ """

    def __init__(self, captcha_secret: str):
        self.secret = captcha_secret
        config = Config()
        self.iplist = config.get_captcha_iplist()

    def _daily_get_iplist(self):
        # no usage now
        return

    def _is_spam_ip(self, ip: str) -> bool:
        spamip = False
        # no usage now
        return False
        with open(self.iplist, "r") as file:
            for line in file:
                if ip in line:
                    spamip = True
                    break
        return spamip

    def _check_ip(self, ip: str) -> bool:
        return False
        from os import path
        import time

        if path.exists(self.iplist):
            oneday = time.mktime(time.localtime()) - path.getmtime(self.iplist)
            if oneday > 24 * 60 * 60:
                self._daily_get_iplist()
                return self._is_spam_ip(ip)
            else:
                return self._is_spam_ip(ip)
        else:
            self._daily_get_iplist()
            return self._is_spam_ip(ip)

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
        # verfiy = False for tests and self signed
        rsp = requests.request("GET", url=url_captcha, params=params, verify=False)
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

        if self._check_ip(remote_ip) == False:
            error = self.validate(remote_ip, response)
        else:
            error = NOT_AUTHORIZED
        if error is not None:
            raise HTTPException(status_code=401, detail=[error])
