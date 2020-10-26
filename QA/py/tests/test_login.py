# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

from starlette import status
from starlette.testclient import TestClient

from tests.credentials import CREATOR_AUTH, ORDINARY_USER2_USER_ID, ADMIN_AUTH
from tests.test_fastapi import USER_ME_URL
from tests.test_subentities import OBJECT_HISTORY_QUERY_URL

LOGIN_URL = "/login"

from main import app

client = TestClient(app)


# Don't use fastapi fixture as it tweaks security
def test_plain_API_login(config, database, caplog):
    url = LOGIN_URL
    # Wrong params
    rsp = client.post(url, data={"usernazme": "foo",
                                 "password": "bar"})
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # OK params, wrong values
    rsp = client.post(url, json={"username": "foo",
                                 "password": "bar"})
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Plaintext password in DB
    rsp = client.post(url, json={"username": "admin",
                                 "password": "nimda"})
    assert rsp.status_code == status.HTTP_200_OK

    # Good password but inactive account
    rsp = client.post(url, json={"username": "old_admin",
                                 "password": "nimda_dlo"})
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Crypted password in DB
    rsp = client.post(url, json={"username": "creator",
                                 "password": "nimda"})
    assert rsp.status_code == status.HTTP_200_OK
    token = rsp.json()
    # Token is quite random (that's good), so below is just a visual example
    # assert token == "eyJ1c2VyX2lkIjoxfQ.X5PMDA.lUsgP1oSyJ4L_qtmoEBXlpd9lIk"
    assert len(token) > 32

    # Ensure that this entry point is not broken from security point of view
    rsp = client.get(USER_ME_URL)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Try the token with an authenticated API call
    rsp = client.get(USER_ME_URL, headers={"Authorization": "Bearer " + token})
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == {'active': True,
                          'country': None,
                          'email': 'creator',
                          'id': 3,
                          'name': 'User Creating Projects',
                          'organisation': None,
                          'usercreationdate': '2020-05-13T08:59:48.701060',
                          'usercreationreason': None}
