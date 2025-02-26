# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
from helpers.httpexception import (
    DETAIL_PASSWORD_STRENGTH_ERROR,
    DETAIL_INVALID_EMAIL,
    DETAIL_EMAIL_OWNED_BY_OTHER,
    DETAIL_INVALID_STATUS,
)
from DB.User import UserStatus
from BO.Rights import NOT_FOUND, NOT_AUTHORIZED
from tests.test_user_admin import (
    USER_UPDATE_URL,
    USER_CREATE_URL,
    USER_GET_URL,
)
from helpers.AppConfig import Config
from tests.credentials import (
    ADMIN_AUTH,
    USER_AUTH,
    USER2_AUTH,
    ORDINARY_USER_USER_ID,
    USERS_ADMIN_USER_ID,
    USERS_ADMIN_AUTH,
)
from API_operations.helpers.UserValidation import UserValidation, ActivationType
import urllib.parse
from tests.test_users import config_captcha

NEW_USER_WITH_CONFIRMATION_ID = 11
NEW_USER_WITH_VALIDATION_ID = 12
URL_RESET_PWD = "/users/reset_user_password"
URL_ACTIVATE = "/users/activate/"
URL_ACTIVATE_USER = "/users/activate/{user_id}/{status}"
LOGIN_URL = "/login"


def set_config_on(monkeypatch, validation="on"):
    def mock_get_account_validation(*args, **kwargs):
        return validation

    def mock_get_user_verification(*args, **kwargs):
        return "on"

    monkeypatch.setattr(
        Config, "get_user_email_verification", mock_get_user_verification
    )
    monkeypatch.setattr(Config, "get_account_validation", mock_get_account_validation)

    # set config user verification on, email verif on - active 0 by default
    def mock_send_mail(*args, **kwargs):
        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
        for arg in args:
            print(arg)
        # raise HTTPException(status_code=200, detail=["sentmail"])
        from helpers.DynamicLogs import get_logger

        logger = get_logger(__name__)
        logger.info("Email sent")

    # _get_ticket
    def mock_get_ticket(*args, **kwargs):
        for arg in args:
            print(arg)
        # raise HTTPException(status_code=200, detail=["sentmail"])
        from helpers.DynamicLogs import get_logger

        logger = get_logger(__name__)
        logger.info("ticket found sent")
        return "ticket_num_xxx"

    from providers.MailProvider import MailProvider

    monkeypatch.setattr(MailProvider, "send_mail", mock_send_mail)
    monkeypatch.setattr(MailProvider, "_get_ticket", mock_get_ticket)

    config_captcha(monkeypatch)


def user_confirm_email(
    fastapi,
    email,
    ref_json,
    url,
    password,
    id,
    action,
    resp_detail,
    resp_code,
    login_code,
    login_detail=None,
):
    # fake token - received in mail  - user cand post a create/update/validate request
    token = UserValidation()._generate_token(email=email, id=id, action=action)
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    if url.find(URL_ACTIVATE) > -1:
        ref_json["token"] = token
    else:
        params["token"] = token

    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=ref_json)
    # user confirm
    if rsp.status_code == 422:
        assert rsp.json() == resp_detail
    assert rsp.status_code == resp_code
    assert rsp.json() == resp_detail

    if login_code is not None:
        # user can login ? depends on user_validation choice
        url = LOGIN_URL
        rsplogin = fastapi.post(url, json={"username": email, "password": password})
        assert rsplogin.status_code == login_code
        if login_code == 200:
            assert len(rsplogin.json()) > 30
        else:
            assert rsplogin.json() == login_detail


def verify_user(fastapi, id, auth, res_user):
    url = "/users?ids=" + str(id)
    rsp = fastapi.get(url, headers=auth)
    assert rsp.status_code == 200
    read_json = rsp.json()
    if len(read_json):
        err = []
        for key, value in res_user.items():
            if read_json[0][key] != value:
                err.append({"key": key, "read": read_json[0][key], "value": value})
        return err
    else:
        return None


def test_user_create_with_confirmation(monkeypatch, fastapi, caplog):
    caplog.set_level(logging.FATAL)
    # modify config to have user validation "off"
    set_config_on(monkeypatch, "off")
    email = "myemail_confirm777@mailtest.provider.net"
    # name is not  "" to bypass ( old version = no more used - one version only)
    usr_json = {
        "id": None,
        "email": email,
        "name": "bypass confirmation",
    }
    url = USER_CREATE_URL
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    # organisation needed
    assert rsp.status_code == 422
    usr_json = {
        "id": None,
        "email": email,
        "name": "bypass confirmation",
        "organisation": "Test Org",
    }

    url = USER_CREATE_URL
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    # verification mail is  always sent if email_verification is on in config
    assert rsp.json() is None
    assert rsp.status_code == 200

    # admin find a user and modify his email
    url = USER_GET_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = {
        "email": "user",
        "id": ORDINARY_USER_USER_ID,
        "name": "Ordinary User",
        "organisation": "org2",
    }
    assert read_json == ref_json
    res_user = {"status": UserStatus.active.value, "mail_status": None}
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    #  no  confirmation email as the update is made by admin even when email_verification is "on" - keep in that order as the status must be 1 for a normal user and is None in db test data
    email = "myemail123@mailtestprovider1.net"
    ref_json["email"] = email
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=ref_json)
    # user status should stay to 1
    assert rsp.json() is None
    assert rsp.status_code == 200
    # so change the user status to inactive to continue the tests
    ref_json["status"] = UserStatus.inactive.value
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    res_user = {"email": email, "status": UserStatus.inactive.value}
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # not authorized
    ref_json["creationreason"] = "test reason"
    rsp = fastapi.put(url, headers=USER2_AUTH, json=ref_json)
    assert rsp.status_code == 403
    assert rsp.json() == {"detail": [NOT_AUTHORIZED]}
    #  user has to confirm email but is deactivated
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.status_code == 403
    assert rsp.json() == {"detail": "You can't do this."}
    # user is inactive and mail_status False
    res_user = {
        "email": email,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    # fake token - received in mail  - user should confirm email
    urlactivate = URL_ACTIVATE_USER.format(user_id=ORDINARY_USER_USER_ID, status="n")
    user_confirm_email(
        fastapi,
        email,
        ref_json={"password": "zero6"},
        url=urlactivate,
        password="zero6",
        id=ORDINARY_USER_USER_ID,
        action=ActivationType.update,
        resp_detail=None,
        resp_code=200,
        login_code=200,
    )
    # mail status should be True as the user was able to confirm
    res_user = {"email": email, "mail_status": True, "status": UserStatus.active.value}
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []

    # user can modify email
    email = "myemail1249@mailtestprovider1.net"
    ref_json["email"] = email
    # ordinary user should not be possible to change status or mail_status explicitly
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    res_user = {
        "email": email,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # and confirm again
    user_confirm_email(
        fastapi,
        email,
        ref_json={"password": "zero6"},
        url=urlactivate,
        password="zero6",
        id=ORDINARY_USER_USER_ID,
        action=ActivationType.update,
        resp_detail=None,
        resp_code=200,
        login_code=200,
    )
    res_user = {"email": email, "mail_status": True, "status": UserStatus.active.value}
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # create user with email verification
    url = USER_CREATE_URL
    email = "itisagoodmailfortestcreate@tesmailfortest1.com"
    password = "Zzzz?a123"
    ref_json = {"email": email, "id": None, "name": "", "organisation": ""}
    rsp = fastapi.post(urlparams, json=ref_json)
    # mail sent to user - request verify email by click on link

    assert rsp.json() is None
    assert rsp.status_code == 200
    ref_json = {
        "email": email,
        "id": None,
        "name": "test create with confirmationonly11",
        "organisation": "test my university",
        "password": password,
    }

    user_confirm_email(
        fastapi,
        email,
        ref_json,
        url,
        password=password,
        id=-1,
        action=ActivationType.create,
        resp_detail=None,
        resp_code=200,
        login_code=200,
    )
    res_user = {"email": email, "mail_status": True, "status": UserStatus.active.value}
    err = verify_user(fastapi, NEW_USER_WITH_CONFIRMATION_ID, ADMIN_AUTH, res_user)
    assert err == []
    # user can MODIFY account data - bad mail format exist in db , but when updating the user must have a valid email
    url = USER_GET_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.get(url, headers=USER_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = read_json
    ref_json["email"] = "useremail@notv"
    ref_json["organisation"] = " test modif no mail confirm organisation"
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)

    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.json() == {"detail": [DETAIL_INVALID_EMAIL]}
    assert rsp.status_code == 422
    email = "itisagoodmailfortestcreate@tesmailfortest2.com"
    ref_json["email"] = email
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.json() is None
    assert rsp.status_code == 200
    res_user = {
        "email": email,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # user confirms email
    url = URL_ACTIVATE_USER.format(user_id=ORDINARY_USER_USER_ID, status="n")
    # fake token - received in mail  - user cant confirm email as password is wrong "NOgoodZzzz?a123" instead of "zero6" - code 403 because of password
    password = "NOgoodZzzz?a123"
    user_confirm_email(
        fastapi,
        email,
        ref_json={"password": password},
        url=url,
        password=password,
        id=ORDINARY_USER_USER_ID,
        action=ActivationType.update,
        resp_detail={"detail": [NOT_AUTHORIZED]},
        resp_code=403,
        login_code=403,
        login_detail={"detail": "You can't do this."},
    )
    res_user = {
        "email": email,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # user confirms email with good password
    password = "zero6"
    user_confirm_email(
        fastapi,
        email,
        ref_json={"password": password},
        url=url,
        password=password,
        id=ORDINARY_USER_USER_ID,
        action=ActivationType.update,
        resp_detail=None,
        resp_code=200,
        login_code=200,
    )
    res_user = {
        "email": email,
        "mail_status": True,
        "status": UserStatus.active.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # admin  activate for next tests
    urlactivate = URL_ACTIVATE_USER
    rsp = fastapi.post(
        urlactivate.format(
            user_id=ORDINARY_USER_USER_ID, status=UserStatus.active.name
        ),
        headers=USERS_ADMIN_AUTH,
        json={},
    )


def test_user_create_with_validation(monkeypatch, fastapi, caplog):
    caplog.set_level(logging.FATAL)
    # modify config to have user validation "on"v
    set_config_on(monkeypatch)
    # Create user email no bot
    url = USER_CREATE_URL
    usr_json = {
        "email": "user@test.mailtest.com",
        "id": None,
        "name": "Ordinary User",
        "organisation": "My Org",
    }
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    # same name is ok - this test becomes useless but ...
    assert rsp.status_code == 200
    assert rsp.json() is None
    # assert rsp.status_code == 422
    # assert rsp.json() == {"detail": [DETAIL_NAME_OWNED_BY_OTHER]}
    usr_json = {
        "id": None,
        "email": "ddduser56w_validation",
        "name": "not good email_validation",
        "organisation": "My Org",
    }
    # note should check password
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.json() == {"detail": [DETAIL_INVALID_EMAIL]}
    assert rsp.status_code == 422
    email = "myemail777@mailtestprovider.net"
    usr_json = {
        "id": None,
        "email": email,
        "name": "",
        "organisation": "My Org",
    }
    rsp = fastapi.post(urlparams, json=usr_json)

    assert rsp.json() is None
    assert rsp.status_code == 200

    # create user with email verification
    url = USER_CREATE_URL
    email = "goodmailfortestcreate@tesmailfortest.com"
    ref_json = {
        "email": email,
        "id": None,
        "name": "",
        "organisation": "My Org",
    }
    rsp = fastapi.post(urlparams, json=ref_json)
    # mail sent to user - request verify email by click on link
    assert rsp.json() is None
    assert rsp.status_code == 200
    ref_json = {
        "email": email,
        "id": None,
        "name": "test create with validation",
        "organisation": "test my university",
        "password": "zzzza123",
    }
    # fake token - received in mail  - user cand post a create request but password is not good

    user_confirm_email(
        fastapi,
        email,
        ref_json,
        url,
        password=None,
        id=-1,
        action=ActivationType.create,
        resp_detail={"detail": [DETAIL_PASSWORD_STRENGTH_ERROR]},
        resp_code=422,
        login_code=None,
    )

    password = "Zzzza?123"
    ref_json["password"] = password
    user_confirm_email(
        fastapi,
        email,
        ref_json,
        url,
        password,
        id=-1,
        action=ActivationType.create,
        resp_detail=None,
        resp_code=200,
        login_code=None,
    )
    # status is 0 waiting for account validation
    res_user = {
        "email": email,
        "mail_status": True,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, NEW_USER_WITH_VALIDATION_ID, ADMIN_AUTH, res_user)
    assert err == []
    # adminv validate user
    # ask more info
    urlactivate = URL_ACTIVATE_USER
    admin_json = {
        "reason": "Please give more reason to create your account, and  email not good"
    }
    rsp = fastapi.post(
        urlactivate.format(
            user_id=NEW_USER_WITH_VALIDATION_ID, status=UserStatus.pending.name
        ),
        headers=USERS_ADMIN_AUTH,
        json=admin_json,
    )
    assert rsp.json() is None
    assert rsp.status_code == 200
    res_user = {"email": email, "mail_status": True, "status": UserStatus.pending.value}
    err = verify_user(fastapi, NEW_USER_WITH_VALIDATION_ID, ADMIN_AUTH, res_user)
    assert err == []
    # user can MODIFY account

    # user modify email
    # user confirm and request validation is sent
    # admin blocks user
    # admin validates user

    rsp = fastapi.post(
        urlactivate.format(
            user_id=NEW_USER_WITH_VALIDATION_ID, status=UserStatus.active.name
        ),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    res_user = {"id": NEW_USER_WITH_VALIDATION_ID, "status": UserStatus.active.value}
    err = verify_user(fastapi, NEW_USER_WITH_VALIDATION_ID, ADMIN_AUTH, res_user)
    assert err == []
    rsp = fastapi.post(
        urlactivate.format(
            user_id=NEW_USER_WITH_VALIDATION_ID, status=UserStatus.blocked.name
        ),
        headers=USERS_ADMIN_AUTH,
        json={},
    )

    assert rsp.json() is None
    assert rsp.status_code == 200
    res_user = {"id": NEW_USER_WITH_VALIDATION_ID, "status": UserStatus.blocked.value}
    err = verify_user(fastapi, NEW_USER_WITH_VALIDATION_ID, ADMIN_AUTH, res_user)
    assert err == []
    # admin find a user and modify his email
    url = USER_GET_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()

    ref_json = {
        "email": "itisagoodmailfortestcreate@tesmailfortest2.com",
        "id": ORDINARY_USER_USER_ID,
        "name": "Ordinary User",
        "organisation": "test modif no mail confirm organisation",
    }
    assert read_json == ref_json
    email_ordinary_user = ref_json["email"]
    ref_json["email"] = email
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": [DETAIL_EMAIL_OWNED_BY_OTHER]}

    # retry with good email and user mod - but user is blocked now
    # block before
    rsp = fastapi.post(
        urlactivate.format(
            user_id=ORDINARY_USER_USER_ID, status=UserStatus.blocked.name
        ),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    res_user = {
        "id": ORDINARY_USER_USER_ID,
        "email": email_ordinary_user,
        "status": UserStatus.blocked.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    ref_json["email"] = "itisagoodmail@tesmailfortest3.com"
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.status_code == 403
    assert rsp.json() == {"detail": "You can't do this."}

    # admin activate useragain
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(
            user_id=ORDINARY_USER_USER_ID, status=UserStatus.active.name
        ),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    res_user = {
        "email": email_ordinary_user,
        "mail_status": True,
        "status": UserStatus.active.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # user can now  modify email
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    email_ordinary_user = ref_json["email"]
    # status is 0 waiting for account validation

    res_user = {
        "email": email_ordinary_user,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # user confirms email but cannot login
    password = "zero6"
    urlactivate = URL_ACTIVATE_USER.format(user_id=ORDINARY_USER_USER_ID, status="n")
    user_confirm_email(
        fastapi,
        email_ordinary_user,
        {"password": password},
        urlactivate,
        password,
        id=ORDINARY_USER_USER_ID,
        action=ActivationType.update,
        resp_detail=None,
        resp_code=200,
        login_code=None,
    )
    # mail_status is True ,status is 0 waiting for account validation
    res_user = {
        "email": email_ordinary_user,
        "mail_status": True,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, ORDINARY_USER_USER_ID, ADMIN_AUTH, res_user)
    assert err == []
    # admin activate useragain
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(
            user_id=ORDINARY_USER_USER_ID, status=UserStatus.active.name
        ),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    # user can now  modify email
    rsp = fastapi.put(url, headers=USER_AUTH, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    ### rest password test
    # user is blocked  ask to reset pwd
    url = URL_RESET_PWD
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    req_json = {"email": email, "id": -1}
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=req_json)
    assert rsp.json() == {"detail": [NOT_FOUND]}
    assert rsp.status_code == 422
    # admin  validates user
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(
            user_id=NEW_USER_WITH_VALIDATION_ID, status=UserStatus.active.name
        ),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.json() is None
    assert rsp.status_code == 200
    # ask reset pwd again -
    rsp = fastapi.post(urlparams, json=req_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    # fake token to test user reset password
    # has to monkeypatch the hash_password from LoginService to have a 200 response status_code
    temp_password = "temp_password"
    token = UserValidation()._generate_token(
        email=email, id=NEW_USER_WITH_VALIDATION_ID, action=temp_password
    )
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"], "token": token}

    req_json = {
        "email": email,
        "id": NEW_USER_WITH_VALIDATION_ID,
        "password": "ZzzzA?123",
    }
    urlparams = url + "?" + urllib.parse.urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=req_json)
    assert rsp.json() == {"detail": [NOT_AUTHORIZED]}
    assert rsp.status_code == 401
