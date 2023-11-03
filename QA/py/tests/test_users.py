# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

import pytest
from API_operations.CRUD.Users import UserService
from helpers.httpexception import DETAIL_EMAIL_OWNED_BY_OTHER, DETAIL_INVALID_EMAIL

from tests.test_import import ADMIN_USER_ID, create_project

from tests.test_user_admin import USER_UPDATE_URL, USER_CREATE_URL, USER_GET_URL


def config_captcha(monkeypatch):
    def mock_verify_captcha(*args, **kwargs):
        from fastapi import HTTPException
        from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

        if len(args) > 1:
            argbot = args[1]
        else:
            argbot = None
        no_bot = list(argbot or ["", ""])
        detail = []
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

    from providers.Google import ReCAPTCHAClient

    monkeypatch.setattr(ReCAPTCHAClient, "verify_captcha", mock_verify_captcha)
    from providers.HomeCaptcha import HomeCaptcha

    monkeypatch.setattr(HomeCaptcha, "verify_captcha", mock_verify_captcha)


def test_prefs_set_get(config, database, fastapi, caplog):

    caplog.set_level(logging.ERROR)
    # Create a dest project
    prj_id = create_project(ADMIN_USER_ID, "Preferences test")
    prefs_for_test = "foo bar boo"
    # Set to something
    with UserService() as sce:
        sce.set_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=prj_id, key="tst", value=prefs_for_test
        )
    # Check it's still there
    with UserService() as sce:
        prefs = sce.get_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=prj_id, key="tst"
        )
        assert prefs == prefs_for_test
        # No error in get if wrong project
        assert "" == sce.get_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=-1, key="tst"
        )
        # No error in get if wrong key
        assert "" == sce.get_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=prj_id, key="test"
        )
        # Error in set if wrong project
        with pytest.raises(Exception):
            sce.set_preferences_per_project(
                user_id=ADMIN_USER_ID, project_id=-1, key="tst", value="crash!"
            )


# test with verif email off  new user
def test_user_create_ordinary(monkeypatch, config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)
    import urllib.parse

    config_captcha(monkeypatch)
    # Create user email no bot
    url = USER_CREATE_URL
    usr_json = {"email": "user", "id": None, "name": "Ordinary User"}
    rsp = fastapi.post(url, json=usr_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": ["reCaptcha verif needs data"]}
    params = {"no_bot": [""]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": ["invalid no_bot reason 1"]}
    strbot = ""
    for i in range(1, 400):
        strbot += str(i)
    params = {"no_bot": ["", strbot]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": ["invalid no_bot reason 2"]}
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": [DETAIL_EMAIL_OWNED_BY_OTHER]}
    usr_json = {
        "id": None,
        "email": "ddduser56",
        "name": "not good email",
    }
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.json() == None
    assert rsp.status_code == 200

    # note should check password
