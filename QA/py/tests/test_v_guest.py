import logging
from helpers.httpexception import DETAIL_EMAIL_OWNED_BY_OTHER

from tests.credentials import ADMIN_AUTH, USER_AUTH, ORDINARY_GUEST_GUEST_ID


# noinspection PyPackageRequirements


GUEST_UPDATE_URL = "/guests/{guest_id}"

GUEST_CREATE_URL = "/guests/create"

GUEST_GET_URL = "/guests"

#WARNING must run after all test_user
def test_guest_create(fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Create as an admin
    url = GUEST_CREATE_URL
    usr_json = {
        "email": "goodmailfortestcreate@tesmailfortest.com",
        "id": None,
        "name": "Ordinary Guest",
        "organisation": "OrgTest",
    }
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=usr_json)
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": [DETAIL_EMAIL_OWNED_BY_OTHER]}
    url = GUEST_CREATE_URL
    usr_json = {
        "id": None,
        "email": "newdddguest5@mailguest.com",
        "name": "Ordinary Guest",
        "organisation": "OrgTest",
    }
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=usr_json)
    assert rsp.status_code == 200
    assert rsp.json() is None

def test_guest_update(fastapi, caplog):
    caplog.set_level(logging.FATAL)

    url = GUEST_GET_URL.format(ids=ORDINARY_GUEST_GUEST_ID)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = [{
        "id": ORDINARY_GUEST_GUEST_ID,
        "email": "newdddguest5@mailguest.com",
        "name": "Ordinary Guest",
        "organisation": "OrgTest",
   'country': None, 'orcid': None
    }]

    assert read_json == ref_json

    # Failing update
    upd_json = {"email": "guest@testmail.guest", "id": ORDINARY_GUEST_GUEST_ID, "organisation": "e", "name": "S",'country': None, 'orcid': None}
    url = GUEST_UPDATE_URL.format(guest_id=ORDINARY_GUEST_GUEST_ID)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == 422
    assert rsp.json() == {
        "detail": [
            "name is too short, 3 chars minimum",
            "organisation is too short, 3 chars minimum",
        ]
    }

    # Self update
    url = GUEST_UPDATE_URL.format(guest_id=ORDINARY_GUEST_GUEST_ID)
    rsp = fastapi.put(url, headers=USER_AUTH, json=read_json)
    assert rsp.status_code == 200
    # actual = rsp.json()
    # assert actual == expected

