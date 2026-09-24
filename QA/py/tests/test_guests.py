from starlette import status
from helpers.httpexception import DETAIL_EMAIL_OWNED_BY_OTHER

from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.test_import import do_test_import

GUEST_UPDATE_URL = "/guests/{guest_id}"
GUEST_CREATE_URL = "/guests/create"
GUEST_LIST_URL = "/guests?ids={ids}"
GUEST_GET_URL = "/guests?ids={ids}"
GUEST_BY_ID_URL = "/guests/{guest_id}"
GUEST_SEARCH_URL = "/guests/search"


def create_guest(
    fastapi,
    email,
    name="Ordinary Guest",
    organisation="OrgTest",
    auth=ADMIN_AUTH,
):
    url = GUEST_CREATE_URL
    usr_json = {
        "id": None,
        "email": email,
        "name": name,
        "organisation": organisation,
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


def test_guest_get_by_id(fastapi):
    # Create a guest to fetch
    email = "guest_for_get_by_id@tesmailfortest.com"
    name = "Guest For Get By Id"
    org = "OrgTestGet"
    rsp = create_guest(fastapi, email, name=name, organisation=org)
    assert rsp.status_code == status.HTTP_200_OK
    guest_id = rsp.json()

    # Unauthenticated request
    url = GUEST_BY_ID_URL.format(guest_id=guest_id)
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Unauthorized (ordinary user) request
    rsp = fastapi.get(url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Non-existent guest id
    not_found_url = GUEST_BY_ID_URL.format(guest_id=999999)
    rsp = fastapi.get(not_found_url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_404_NOT_FOUND
    assert rsp.json() == {"detail": "User not found"}

    # Successful retrieval as admin
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == {
        "id": guest_id,
        "email": email,
        "name": name,
        "organisation": org,
        "country": None,
        "orcid": None,
    }


def test_guest_search(fastapi):
    # Unauthenticated request
    rsp = fastapi.get(GUEST_SEARCH_URL)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Unauthorized (ordinary user) request
    rsp = fastapi.get(GUEST_SEARCH_URL, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Admin request without by_name parameter returns empty list
    rsp = fastapi.get(GUEST_SEARCH_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == []

    # Admin request with non-matching name returns empty list
    rsp = fastapi.get(
        GUEST_SEARCH_URL,
        headers=ADMIN_AUTH,
        params={"by_name": "%NonExistentGuestName%"},
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == []

    # Create project, collection, and associate guest to test search results
    prj_id = do_test_import(
        fastapi, "Search guest test project", instrument="Other scanner"
    )
    coll_rsp = fastapi.post(
        "/collections/create",
        headers=ADMIN_AUTH,
        json={"title": "Search Guest Test Collection", "project_ids": [prj_id]},
    )
    assert coll_rsp.status_code == status.HTTP_200_OK
    coll_id = coll_rsp.json()

    guest_email = "searchable_guest@tesmailfortest.com"
    guest_name = "Searchable Guest Unique"
    guest_org = "OrgSearchTest"
    guest_rsp = create_guest(
        fastapi,
        guest_email,
        name=guest_name,
        organisation=guest_org,
    )
    assert guest_rsp.status_code == status.HTTP_200_OK
    guest_id = guest_rsp.json()

    # Associate guest to collection
    rsp = fastapi.get(f"/collections/{coll_id}", headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    coll_data = rsp.json()
    if "display_order" in coll_data:
        del coll_data["display_order"]
    coll_data["creator_users"] = [guest_id]
    upd_rsp = fastapi.put(
        f"/collections/{coll_id}",
        headers=ADMIN_AUTH,
        json=coll_data,
    )
    assert upd_rsp.status_code == status.HTTP_200_OK

    # Search by exact/partial name with wildcards
    rsp = fastapi.get(
        GUEST_SEARCH_URL,
        headers=ADMIN_AUTH,
        params={"by_name": "%Searchable Guest%"},
    )
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    assert isinstance(results, list)
    matching = [g for g in results if g["id"] == guest_id]
    assert len(matching) == 1
    assert matching[0] == {
        "id": guest_id,
        "email": guest_email,
        "name": guest_name,
        "organisation": guest_org,
        "country": None,
        "orcid": None,
    }

    # Case-insensitive search
    rsp = fastapi.get(
        GUEST_SEARCH_URL,
        headers=ADMIN_AUTH,
        params={"by_name": "%searchable%"},
    )
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    matching = [g for g in results if g["id"] == guest_id]
    assert len(matching) == 1
