from helpers.httpexception import DETAIL_EMAIL_OWNED_BY_OTHER

from tests.credentials import ADMIN_AUTH, USER_AUTH

GUEST_UPDATE_URL = "/guests/{guest_id}"
GUEST_CREATE_URL = "/guests/create"
GUEST_GET_URL = "/guests?ids={ids}"


def create_guest(fastapi, email, auth=ADMIN_AUTH):
    url = GUEST_CREATE_URL
    usr_json = {
        "id": None,
        "email": email,
        "name": "Ordinary Guest",
        "organisation": "OrgTest",
    }
    rsp = fastapi.post(url, headers=auth, json=usr_json)
    return rsp


def test_guest_create(fastapi):

    # Create as an admin but email is already in DB
    rsp = create_guest(fastapi, "real@users.com")
    assert rsp.status_code == 422
    assert rsp.json() == {"detail": [DETAIL_EMAIL_OWNED_BY_OTHER]}

    rsp = create_guest(fastapi, "guest_for_create@tesmailfortest.com")
    assert rsp.status_code == 200
    assert isinstance(rsp.json(), int)


def test_guest_update(fastapi):

    rsp = create_guest(fastapi, "guest_for_update@tesmailfortest.com")
    assert rsp.status_code == 200
    guest_id = rsp.json()

    url = GUEST_GET_URL.format(ids=guest_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = [
        {
            "id": guest_id,
            "email": "guest_for_update@tesmailfortest.com",
            "name": "Ordinary Guest",
            "organisation": "OrgTest",
            "country": None,
            "orcid": None,
        }
    ]

    assert read_json == ref_json

    # Failing update - bad data
    upd_json = {
        "email": "guest@testmail.guest",
        "id": guest_id,
        "organisation": "e",
        "name": "S",
    }
    url = GUEST_UPDATE_URL.format(guest_id=guest_id)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == 422
    assert rsp.json() == {
        "detail": [
            "name is too short, 3 chars minimum",
            "organisation is too short, 3 chars minimum",
        ]
    }

    # Failing update - no right
    upd_json.update(
        {"country": "France", "name": "Ordinary Guest", "organisation": "OrgTest"}
    )
    url = GUEST_UPDATE_URL.format(guest_id=guest_id)
    # not manager of projects in collections where the guest is registered
    rsp = fastapi.put(url, headers=USER_AUTH, json=upd_json)
    assert rsp.status_code == 403

    # TODO: Business rules are unclear
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == 200
    assert rsp.json() is None
