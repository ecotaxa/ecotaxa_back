import logging
from helpers.httpexception import DETAIL_EMAIL_OWNED_BY_OTHER

from tests.credentials import ADMIN_AUTH, USER_AUTH, ORDINARY_USER_USER_ID


# noinspection PyPackageRequirements


USER_UPDATE_URL = "/users/{user_id}"

USER_CREATE_URL = "/users/create"

USER_GET_URL = "/users/{user_id}"


def test_user_update(fastapi, caplog):
    caplog.set_level(logging.FATAL)

    url = USER_GET_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = {"email": "user", "id": 2, "name": "Ordinary User"}
    assert read_json == ref_json

    # Failing update
    upd_json = {"email": "user", "id": 2, "organisation": "e", "name": "S"}
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=USER_AUTH, json=upd_json)
    assert rsp.status_code == 422
    assert rsp.json() == {
        "detail": [
            "name is too short, 3 chars minimum",
            "organisation is too short, 3 chars minimum",
        ]
    }

    # Self update
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=USER_AUTH, json=read_json)
    assert rsp.status_code == 200
    # actual = rsp.json()
    # assert actual == expected


def test_user_create(fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Create as an admin
    url = USER_CREATE_URL
    usr_json = {"email": "user", "id": None, "name": "Ordinary User"}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=usr_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": [DETAIL_EMAIL_OWNED_BY_OTHER]}
    url = USER_CREATE_URL
    usr_json = {
        "id": None,
        "email": "ddduser5",
        "name": "Application Administrator Now Retired",
    }
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=usr_json)
    assert rsp.status_code == 200
    assert rsp.json() == None
