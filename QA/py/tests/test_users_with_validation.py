# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

import pytest
from API_operations.CRUD.Users import UserService
from tests.test_user_admin import USER_UPDATE_URL, USER_CREATE_URL, USER_GET_URL
from helpers.AppConfig import Config
from fastapi import HTTPException
from tests.credentials import ADMIN_AUTH, USER_AUTH, ORDINARY_USER_USER_ID
from API_operations.helpers.UserValidation import (
    UserValidation,
    ACTIVATION_ACTION_CREATE,
    ACTIVATION_ACTION_UPDATE,
    ACTIVATION_ACTION_ACTIVE,
    ACTIVATION_ACTION_DESACTIVE,
    ACTIVATION_ACTION_HASTOMODIFY,
)

URL_RESET_PWD = "/users/reset_user_password"


def set_config_on(monkeypatch):
    def mock_get_account_activate_email(*args, **kwargs):
        return "testmailaccountuseradmin@externatltstsvalidationtiocket.com"

    def mock_get_user_verification(*args, **kwargs):
        return "on"

    def mock_get_account_active_unset(*args, **kwargs):
        return "on"

    monkeypatch.setattr(
        Config,
        "get_account_activate_email",
        mock_get_account_activate_email,
    )
    monkeypatch.setattr(
        Config, "get_user_email_verification", mock_get_user_verification
    )
    monkeypatch.setattr(
        Config, "get_account_active_unset", mock_get_account_active_unset
    )

    # set config user verification on, email verif on - active False by default

    def mock_send_mail(*args, **kwargs):
        raise HTTPException(status_code=202, detail=["sentmail"])
        from helpers.DynamicLogs import get_logger

        logger = get_logger(__name__)
        logger.info("Email sent")

    from providers.MailProvider import MailProvider

    monkeypatch.setattr(MailProvider, "send_mail", mock_send_mail)


def test_user_create_ordinary_with_validation(
    monkeypatch, config, database, fastapi, caplog
):
    caplog.set_level(logging.FATAL)
    import urllib.parse

    # modify config to have user validation "on"v
    set_config_on(monkeypatch)
    # Create user email no bot
    url = USER_CREATE_URL
    usr_json = {"email": "user", "id": None, "name": "Ordinary User"}
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": ["email already corresponds to another user"]}
    usr_json = {
        "id": None,
        "email": "ddduser56w_validation",
        "name": "not good email_validation",
    }
    # note should check password
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.json() == {"detail": ["Email is invalid"]}
    assert rsp.status_code == 422

    email = "myemail777@mailtestprovider.net"
    usr_json = {
        "id": None,
        "email": email,
        "name": "send verifmail",
    }
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.status_code == 202
    assert rsp.json() == {"detail": ["sentmail"]}
    # admin find a user and modify his email
    url = USER_GET_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = {"email": "user", "id": 2, "name": "Ordinary User"}
    assert read_json == ref_json
    ref_json["email"] = email
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": ["email already corresponds to another user"]}
    # create user with email verification
    url = USER_CREATE_URL
    email = "goodmailfortestcreate@tesmailfortest.com"
    ref_json = {"email": email, "id": None, "name": ""}
    rsp = fastapi.post(urlparams, json=ref_json)
    # mail sent to user - request verify email by click on link
    assert rsp.json() == {"detail": ["sentmail"]}
    assert rsp.status_code == 202
    # ref_json = {
    #    "email": email,
    #    "id": None,
    #    "name": "test create with validation",
    #    "organisation": " test my university",
    #    "password": "zzzza123",
    # }
    # fake token - received in mail  - user cand post a create request
    # token = UserValidation()._generate_token(
    #    email=email, id=-1, action=ACTIVATION_ACTION_CREATE
    # )
    # params = {"no_bot": ["193.4.123.4", "sdfgdqsg"], "token": token}
    # urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    # rsp = fastapi.post(urlparams, json=ref_json)
    # mail sent to user admin - request_activation
    # assert rsp.status_code == 202
    # assert rsp.json() == {"detail": ["sentmail"]}
    # TODO -verify if the user has been created and active is 0
    # TODO users admin activate the user
    # TODO users admin discard the user and ask to modify data - user_has_to_modify
    # admin - modify with a valid email
    # email = "goodmailfortestupdate@tesmailfortest.com"
    # ref_json["email"] = email
    # ref_json["id"] = int(11)
    # rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    # user modified  active = false - request to activate sent to users admin
    # assert rsp.json() == {"detail": ["sentmail"]}
    # assert rsp.status_code == 202
    # TODO -
    # -
    # user ask to reset pwd - will be done after - table reset_user_password missing for tests - trouble with alembic version number file script.py.mako missing
    # url = URL_RESET_PWD
    # params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    # req_json = {"email": email, "id": -1}
    # urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    # rsp = fastapi.post(urlparams, json=req_json)
    # assert rsp.json() == {"detail": ["sentmail"]}
    # assert rsp.status_code == 202

    # mock token to test user reset password
