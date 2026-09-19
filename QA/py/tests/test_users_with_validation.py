# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from urllib.parse import urlencode

from BO.Rights import NOT_FOUND, NOT_AUTHORIZED
from DB.User import UserStatus
from helpers.AppConfig import Config
from helpers.httpexception import (
    DETAIL_PASSWORD_STRENGTH_ERROR,
    DETAIL_INVALID_EMAIL,
    DETAIL_EMAIL_OWNED_BY_OTHER,
)

from tests.credentials import (
    ADMIN_AUTH,
    USER2_AUTH,
    USERS_ADMIN_AUTH,
)
from tests.test_user_admin import (
    USER_UPDATE_URL,
    USER_CREATE_URL,
    USER_GET_URL,
)
from tests.test_users import config_captcha

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

    captured_tokens = []
    orig_populate_mail_message = MailProvider._populate_mail_message

    def spy_populate_mail_message(self, model_name, values, *args, **kwargs):
        token = getattr(values, "token", None)
        if token is not None:
            captured_tokens.append(token)
        return orig_populate_mail_message(self, model_name, values, *args, **kwargs)

    monkeypatch.setattr(MailProvider, "send_mail", mock_send_mail)
    monkeypatch.setattr(MailProvider, "_get_ticket", mock_get_ticket)
    monkeypatch.setattr(
        MailProvider, "_populate_mail_message", spy_populate_mail_message
    )

    config_captcha(monkeypatch)

    def get_last_token():
        return captured_tokens[-1] if captured_tokens else None

    return get_last_token


def user_confirm_email(
    fastapi,
    email,
    ref_json,
    url,
    password,
    token,
    expected_rsp_code,
    expected_rsp_detail=None,
    expected_login_code=None,
    expected_login_detail=None,
):
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    if url.find(URL_ACTIVATE) > -1:
        ref_json["token"] = token
    else:
        params["token"] = token

    urlparams = url + "?" + urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=ref_json)
    # user confirmation
    assert rsp.status_code == expected_rsp_code
    assert rsp.json() == expected_rsp_detail

    if expected_login_code is not None:
        # user can login ? depends on user_validation choice
        url = LOGIN_URL
        rsplogin = fastapi.post(url, json={"username": email, "password": password})
        assert rsplogin.status_code == expected_login_code
        if expected_login_code == 200:
            assert len(rsplogin.json()) > 30
        else:
            assert rsplogin.json() == expected_login_detail


def create_db_user(
    email="test_db_user@test.org",
    name="Test DB User",
    organisation="Test Org",
    password="Password123!",
    status=UserStatus.active.value,
    mail_status=True,
    usercreationreason="Test reason",
    country="France",
) -> int:
    # Create a test user directly in DB, returning its ID
    from API_operations.CRUD.Users import UserService
    from DB.User import User
    from helpers import DateTime
    from BO.User import UserBO

    with UserService() as sce:
        user = User()
        user.email = email
        user.name = name
        user.country = country
        user.usercreationreason = usercreationreason
        user.status = status.value if isinstance(status, UserStatus) else status
        user.mail_status = mail_status
        user.usercreationdate = DateTime.now_time()
        if organisation:
            user.organization_id = UserBO.get_organization_id(sce.session, organisation)
        user.password = password
        sce.session.add(user)
        sce.session.commit()
        return user.id


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


def search_user_id_by_name(fastapi, name, auth=ADMIN_AUTH):
    url = "/users"  # Cannot use /users/search which filters by active status
    rsp = fastapi.get(url, headers=auth)
    assert rsp.status_code == 200
    ret = None
    for usr in rsp.json():
        if usr["name"] == name:
            ret = usr["id"]
    return ret


def test_user_create_with_confirmation(monkeypatch, fastapi):
    # modify config to have user validation "off"
    get_last_token = set_config_on(monkeypatch, "off")
    email = "myemail_confirm777@mailtest.provider.net"
    # name is not  "" to bypass ( old version = no more used - one version only)
    usr_json = {
        "id": None,
        "email": email,
        "name": "bypass confirmation",
    }
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = USER_CREATE_URL + "?" + urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    # organisation needed
    assert rsp.status_code == 422
    usr_json = {
        "id": None,
        "email": email,
        "name": "bypass confirmation",
        "organisation": "Test Org",
    }

    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = USER_CREATE_URL + "?" + urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    # verification mail is always sent if email_verification is on in config
    assert rsp.json() is None
    assert rsp.status_code == 200

    # create user with email verification
    email = "itisagoodmailfortestcreate@tesmailfortest1.com"
    password = "Zzzz?a123"
    ref_json = {"email": email, "id": None, "name": "", "organisation": ""}
    rsp = fastapi.post(urlparams, json=ref_json)
    # mail sent to user - a request to verify email by clicking on link
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
        ref_json=ref_json,
        url=USER_CREATE_URL,
        password=password,
        token=get_last_token(),
        expected_rsp_code=200,
        expected_login_code=200,
    )

    new_user_id = search_user_id_by_name(fastapi, "test create with confirmationonly11")
    res_user = {"email": email, "mail_status": True, "status": UserStatus.active.value}
    err = verify_user(fastapi, new_user_id, ADMIN_AUTH, res_user)
    assert err == []


def test_user_update_with_confirmation(monkeypatch, fastapi):
    # modify config to have user validation "off"
    get_last_token = set_config_on(monkeypatch, "off")

    db_user_id = create_db_user(
        email="ordinary_user_confirmation@test.org",
        name="Ordinary User Confirmation",
        organisation="Test Org",
        password="zero6",
        status=UserStatus.active.value,
        mail_status=None,
    )

    # admin finds a user and modify his email
    url = USER_GET_URL.format(user_id=db_user_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = {
        "email": "ordinary_user_confirmation@test.org",
        "id": db_user_id,
        "name": "Ordinary User Confirmation",
        "organisation": "Test Org",
    }
    assert read_json == ref_json
    res_user = {"status": UserStatus.active.value, "mail_status": None}
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []

    # no confirmation email as the update is from an admin even when email_verification is "on"
    # keep in that order as the status must be 1 for a normal user and is None in db test data
    email = "myemail123@mailtestprovider1.net"
    ref_json["email"] = email
    url = USER_UPDATE_URL.format(user_id=db_user_id)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=ref_json)
    # user status should stay to 1
    assert rsp.json() is None
    assert rsp.status_code == 200

    # change the user status to inactive, to continue the tests
    ref_json["status"] = UserStatus.inactive.value
    url = USER_UPDATE_URL.format(user_id=db_user_id)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    res_user = {"email": email, "status": UserStatus.inactive.value}
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # not authorized
    ref_json["creationreason"] = "test reason"
    rsp = fastapi.put(url, headers=USER2_AUTH, json=ref_json)
    assert rsp.status_code == 403
    assert rsp.json() == {"detail": [NOT_AUTHORIZED]}

    # user has to confirm email but is deactivated
    user_auth = {"Authorization": "Bearer " + str(db_user_id)}
    url = USER_UPDATE_URL.format(user_id=db_user_id)
    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.status_code == 403
    assert rsp.json() == {"detail": "You can't do this."}
    # user is inactive and mail_status False
    res_user = {
        "email": email,
        "mail_status": None,  # TODO: Bug?
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []

    # admin activates the user again
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=db_user_id, status=UserStatus.active.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.status_code == 200
    res_user = {
        "email": email,
        "status": UserStatus.active.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []

    # user can modify own email
    email = "myemail1249@mailtestprovider1.net"
    ref_json["email"] = email
    # ordinary user should not be able to change status or mail_status explicitly
    url = USER_UPDATE_URL.format(user_id=db_user_id)
    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    res_user = {
        "email": email,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # and confirm again
    urlactivate = URL_ACTIVATE_USER.format(user_id=db_user_id, status="n")
    user_confirm_email(
        fastapi,
        email,
        ref_json={"password": "zero6"},
        url=urlactivate,
        password="zero6",
        token=get_last_token(),
        expected_rsp_code=200,
        expected_login_code=200,
    )
    res_user = {
        "email": email,
        "mail_status": True,
        "status": UserStatus.active.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []

    # user can MODIFY account data - bad mail format exists in db, but when updating the user must have a valid email
    url = USER_GET_URL.format(user_id=db_user_id)
    rsp = fastapi.get(url, headers=user_auth)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = read_json
    ref_json["email"] = "useremail@notv"
    ref_json["organisation"] = " test modif no mail confirm organisation"
    url = USER_UPDATE_URL.format(user_id=db_user_id)

    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.json() == {"detail": [DETAIL_INVALID_EMAIL]}
    assert rsp.status_code == 422
    email = "itisagoodmailfortestcreate@tesmailfortest2.com"
    ref_json["email"] = email
    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.json() is None
    assert rsp.status_code == 200
    res_user = {
        "email": email,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # user confirms email
    url = URL_ACTIVATE_USER.format(user_id=db_user_id, status="n")
    # fake token - received in mail  - user cant confirm email as password is wrong "NOgoodZzzz?a123" instead of "zero6" - code 403 because of password
    password = "NOgoodZzzz?a123"
    user_confirm_email(
        fastapi,
        email,
        ref_json={"password": password},
        url=url,
        password=password,
        token=get_last_token(),
        expected_rsp_code=403,
        expected_rsp_detail={"detail": [NOT_AUTHORIZED]},
        expected_login_code=403,
        expected_login_detail={"detail": "You can't do this."},
    )
    res_user = {
        "email": email,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # user confirms email with good password
    password = "zero6"
    user_confirm_email(
        fastapi,
        email,
        ref_json={"password": password},
        url=url,
        password=password,
        token=get_last_token(),
        expected_rsp_code=200,
        expected_login_code=200,
    )
    res_user = {
        "email": email,
        "mail_status": True,
        "status": UserStatus.active.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # admin activate for next tests
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=db_user_id, status=UserStatus.active.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.status_code == 200


def test_user_create_with_validation(monkeypatch, fastapi):
    # modify config to have user validation "on"
    get_last_token = set_config_on(monkeypatch)
    # Create user email no bot
    usr_json = {
        "email": "user@test.mailtest.com",
        "id": None,
        "name": "Ordinary User",
        "organisation": "My Org",
    }
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = USER_CREATE_URL + "?" + urlencode(params, doseq=True)
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

    usr_json = {
        "id": None,
        "email": "myemail777@mailtestprovider.net",
        "name": "",
        "organisation": "My Org",
    }
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.json() is None
    assert rsp.status_code == 200

    # create user with email verification
    email = "goodmailfortestcreate@tesmailfortest.com"
    ref_json = {
        "id": None,
        "email": email,
        "name": "",
        "organisation": "My Org",
    }
    rsp = fastapi.post(urlparams, json=ref_json)
    # mail sent to user - a request to verify email by clicking on a link
    assert rsp.json() is None
    assert rsp.status_code == 200

    # fake token - received in mail - user can post a creation request but password is not good
    ref_json = {
        "id": None,
        "email": email,
        "name": "test create with validation",
        "organisation": "test my university",
        "password": "zzzza123",
    }
    user_confirm_email(
        fastapi,
        email,
        ref_json=ref_json,
        url=USER_CREATE_URL,
        password=None,
        token=get_last_token(),
        expected_rsp_code=422,
        expected_rsp_detail={"detail": [DETAIL_PASSWORD_STRENGTH_ERROR]},
    )  # Cannot confirm email with a weak password

    password = "Zzzza?123"
    ref_json["password"] = password
    user_confirm_email(
        fastapi,
        email,
        ref_json=ref_json,
        url=USER_CREATE_URL,
        password=password,
        token=get_last_token(),
        expected_rsp_code=200,
    )

    new_user_id = search_user_id_by_name(fastapi, "test create with validation")

    # status is 0 waiting for account validation
    res_user = {
        "email": email,
        "mail_status": True,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, new_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # admin validates user
    # ask more info

    admin_json = {
        "reason": "Please give more reason to create your account, and  email not good"
    }
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=new_user_id, status=UserStatus.pending.name),
        headers=USERS_ADMIN_AUTH,
        json=admin_json,
    )
    assert rsp.json() is None
    assert rsp.status_code == 200
    res_user = {"email": email, "mail_status": True, "status": UserStatus.pending.value}
    err = verify_user(fastapi, new_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # user can MODIFY account

    # user modify email
    # user confirm and request validation is sent
    # admin blocks user
    # admin validates user

    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=new_user_id, status=UserStatus.active.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.status_code == 200
    res_user = {"id": new_user_id, "status": UserStatus.active.value}
    err = verify_user(fastapi, new_user_id, ADMIN_AUTH, res_user)
    assert err == []
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=new_user_id, status=UserStatus.blocked.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.json() is None
    assert rsp.status_code == 200

    res_user = {"id": new_user_id, "status": UserStatus.blocked.value}
    err = verify_user(fastapi, new_user_id, ADMIN_AUTH, res_user)
    assert err == []

    # reset password test
    # user is blocked, asks to reset pwd
    url = URL_RESET_PWD
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    req_json = {"email": email, "id": -1}
    urlparams = url + "?" + urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=req_json)
    assert rsp.json() == {"detail": [NOT_FOUND]}
    assert rsp.status_code == 422
    # admin validates user
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=new_user_id, status=UserStatus.active.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.json() is None
    assert rsp.status_code == 200
    # ask reset pwd again -
    rsp = fastapi.post(urlparams, json=req_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"], "token": get_last_token()}

    req_json = {
        "email": email,
        "id": new_user_id,
        "password": "ZzzzA?123",
    }
    urlparams = url + "?" + urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=req_json)
    assert rsp.json() is None
    assert rsp.status_code == 200

    # verify user can login with new password
    login_rsp = fastapi.post(
        LOGIN_URL, json={"username": email, "password": "ZzzzA?123"}
    )
    assert login_rsp.status_code == 200


def test_user_update_with_validation(fastapi, monkeypatch):
    # modify config to have user validation "on"
    get_last_token = set_config_on(monkeypatch)

    db_user_id = create_db_user(
        email="ordinary_user_validation@test.org",
        name="Ordinary User Validation",
        organisation="Test Org",
        password="zero6",
        status=UserStatus.active.value,
        mail_status=True,
    )

    # admin finds a user and modifies his email
    url = USER_GET_URL.format(user_id=db_user_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()

    # user updates himself
    user_auth = {"Authorization": "Bearer " + str(db_user_id)}
    ref_json = {
        "email": "ordinary_user_validation@test.org",
        "id": db_user_id,
        "name": "Ordinary User Validation",
        "organisation": "Test Org",
    }
    assert read_json == ref_json
    email_ordinary_user = ref_json["email"]
    ref_json["email"] = "real@users.com"
    url = USER_UPDATE_URL.format(user_id=db_user_id)
    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": [DETAIL_EMAIL_OWNED_BY_OTHER]}

    # retry with good email and user mod - but user is blocked now
    # block before
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=db_user_id, status=UserStatus.blocked.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.status_code == 200
    res_user = {
        "id": db_user_id,
        "email": email_ordinary_user,
        "status": UserStatus.blocked.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    ref_json["email"] = "itisagoodmail@tesmailfortest3.com"
    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.status_code == 403
    assert rsp.json() == {"detail": "You can't do this."}

    # admin activates the user again
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=db_user_id, status=UserStatus.active.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.status_code == 200
    res_user = {
        "email": email_ordinary_user,
        "mail_status": True,
        "status": UserStatus.active.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # user can now modify own email
    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
    email_ordinary_user = ref_json["email"]
    # status is 0 waiting for account validation

    res_user = {
        "email": email_ordinary_user,
        "mail_status": False,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # user confirms email but cannot login
    password = "zero6"
    urlactivate = URL_ACTIVATE_USER.format(user_id=db_user_id, status="n")
    user_confirm_email(
        fastapi,
        email_ordinary_user,
        ref_json={"password": password},
        url=urlactivate,
        password=password,
        token=get_last_token(),
        expected_rsp_code=200,
    )
    # mail_status is True, status is 0 waiting for account validation
    res_user = {
        "email": email_ordinary_user,
        "mail_status": True,
        "status": UserStatus.inactive.value,
    }
    err = verify_user(fastapi, db_user_id, ADMIN_AUTH, res_user)
    assert err == []
    # admin activate user again
    rsp = fastapi.post(
        URL_ACTIVATE_USER.format(user_id=db_user_id, status=UserStatus.active.name),
        headers=USERS_ADMIN_AUTH,
        json={},
    )
    assert rsp.status_code == 200
    # user can now modify own email
    rsp = fastapi.put(url, headers=user_auth, json=ref_json)
    assert rsp.status_code == 200
    assert rsp.json() is None


def test_create_with_bogus_token_is_refused(monkeypatch, fastapi):
    set_config_on(monkeypatch, "off")
    # vérification d'email active
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"], "token": "not-a-token"}
    body = {
        "id": None,
        "email": "forged@victim.org",
        "name": "Forged Account",
        "organisation": "Somewhere",
        "password": "Zzzza?123",
    }
    url = USER_CREATE_URL + "?" + urlencode(params, doseq=True)
    rsp = fastapi.post(url, json=body)
    assert rsp.status_code == 403


def test_set_config_on_spies_token(monkeypatch, fastapi):
    get_last_token = set_config_on(monkeypatch, "off")
    assert get_last_token() is None

    usr_json = {
        "id": None,
        "email": "spy_token_test@mailtest.provider.net",
        "name": "Spy Token User",
        "organisation": "Test Org",
    }
    params = {"no_bot": ["193.4.123.4", "sdfgdqsg"]}
    urlparams = USER_CREATE_URL + "?" + urlencode(params, doseq=True)
    rsp = fastapi.post(urlparams, json=usr_json)
    assert rsp.status_code == 200
    assert len(get_last_token()) > 0
