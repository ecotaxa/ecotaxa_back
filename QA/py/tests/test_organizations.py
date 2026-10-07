# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

import pytest
from starlette import status
from tests.credentials import ADMIN_AUTH, USER_AUTH, ORDINARY_USER_USER_ID

from providers.EDMO import EDMOFetcher, EDMOOrganization

ORGANIZATIONS_SEARCH_URL = "/organizations/search"
ORGANIZATIONS_LIST_URL = "/organizations"
ORGANIZATION_CREATE_URL = "/organizations/create"
ORGANIZATION_UPDATE_URL = "/organizations/{organization_id}"


@pytest.fixture(autouse=True)
def no_edmo(mocker):
    """No access to the real EDMO, nothing found there unless a test says otherwise"""
    return mocker.patch.object(EDMOFetcher, "_query", return_value=[])


def test_organizations_search(fastapi):
    # Search with % to get some results. search_organizations endpoint is open.
    params = {"name": "%"}
    rsp = fastapi.get(ORGANIZATIONS_SEARCH_URL, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    assert isinstance(results, list)
    # results from search_organizations are List[OrganizationModel]
    if results:
        org = results[0]
        assert "id" in org
        assert "name" in org


def test_organization_crud(fastapi):
    # 1. Create organization as Admin
    new_org_name = "Test Organization CRUD UNIQUE"
    org_data = {"id": -1, "name": new_org_name, "directories": "edmo:1234"}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert (
        rsp.status_code == status.HTTP_200_OK
    ), f"Failed to create organization: {rsp.text}"
    org_id = rsp.json()
    assert isinstance(org_id, int)
    assert org_id > 0

    # 2. Get the organization (List endpoint)
    params = {"ids": str(org_id)}
    rsp = fastapi.get(ORGANIZATIONS_LIST_URL, headers=ADMIN_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    assert len(results) >= 1
    # Find our org in results
    org = next((o for o in results if o["id"] == org_id), None)
    assert org is not None
    assert org["name"] == new_org_name
    assert org["directories"] == "edmo:1234"

    # 3. Update the organization
    updated_name = "Updated Test Organization UNIQUE"
    update_data = {"id": org_id, "name": updated_name, "directories": "edmo:5678"}
    url = ORGANIZATION_UPDATE_URL.format(organization_id=org_id)
    # Users can't
    rsp = fastapi.put(url, headers=USER_AUTH, json=update_data)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    # Admin can
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=update_data)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() is None

    # 4. Verify update
    rsp = fastapi.get(ORGANIZATIONS_LIST_URL, headers=ADMIN_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    org = next((o for o in results if o["id"] == org_id), None)
    assert org["name"] == updated_name
    assert org["directories"] == "edmo:5678"


def test_organization_create_unauthorized(fastapi):
    # Ordinary user cannot create organization
    org_data = {"id": -1, "name": "Unauthorized Org", "directories": None}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=USER_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    # Nor unlogged user
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, json=org_data)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN


def test_organization_create_registration_token(fastapi, monkeypatch):
    from API_operations.helpers.UserValidation import UserValidation, ActivationType
    from tests.test_users_with_validation import set_config_on

    set_config_on(monkeypatch)
    org_data = {"id": -1, "name": "Registering user Org", "directories": None}
    # Bad token
    rsp = fastapi.post(
        ORGANIZATION_CREATE_URL, params={"token": "bogus"}, json=org_data
    )
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    # Unlogged user creating an account, with the token sent by email
    token = UserValidation()._generate_token(
        "new@plankton.org", action=ActivationType.create.value
    )
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, params={"token": token}, json=org_data)
    assert rsp.status_code == status.HTTP_200_OK
    rsp = fastapi.get(
        ORGANIZATIONS_SEARCH_URL, params={"name": "Registering user Org"}
    )
    assert [org["name"] for org in rsp.json()] == ["Registering user Org"]


def test_organization_create_invalid(fastapi):
    # 1. Create with no name (empty name)
    org_data = {"id": -1, "name": "", "directories": None}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    org_data = {"id": -1, "name": "   ", "directories": None}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # 2. Create with existing name
    # First, create one
    new_org_name = "Duplicate Name Org"
    org_data = {"id": -1, "name": new_org_name, "directories": None}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_200_OK

    # Try to create another one with same name
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def _created_org(fastapi, org_data):
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    org_id = rsp.json()
    rsp = fastapi.get(
        ORGANIZATIONS_LIST_URL, headers=ADMIN_AUTH, params={"ids": str(org_id)}
    )
    assert rsp.status_code == status.HTTP_200_OK
    return next(o for o in rsp.json() if o["id"] == org_id)


def test_organization_create_found_in_edmo_by_name(fastapi, mocker):
    found = mocker.patch.object(
        EDMOFetcher,
        "find_by_name",
        return_value=[EDMOOrganization(9901, "EDMO Named Institute")],
    )
    org = _created_org(
        fastapi, {"id": -1, "name": " edmo named institute ", "directories": None}
    )
    found.assert_called_once_with(" edmo named institute ")
    assert org["name"] == "EDMO Named Institute"
    assert org["directories"] == "edmo:9901"


def test_organization_create_found_in_edmo_by_code(fastapi, mocker):
    by_name = mocker.patch.object(EDMOFetcher, "find_by_name")
    by_code = mocker.patch.object(
        EDMOFetcher,
        "get_by_code",
        return_value=EDMOOrganization(9902, "EDMO Coded Institute"),
    )
    org = _created_org(
        fastapi,
        {"id": -1, "name": "Coded inst.", "directories": "ror:0abcdefgh, edmo:9902"},
    )
    by_code.assert_called_once_with(9902)
    by_name.assert_not_called()
    assert org["name"] == "EDMO Coded Institute"
    assert org["directories"] == "edmo:9902,ror:0abcdefgh"


def test_organization_create_not_decided_by_edmo(fastapi, mocker):
    # Ambiguous name in EDMO: the organization is created as given
    mocker.patch.object(
        EDMOFetcher,
        "find_by_name",
        return_value=[
            EDMOOrganization(9903, "Twin Institute"),
            EDMOOrganization(9904, "TWIN INSTITUTE"),
        ],
    )
    org = _created_org(
        fastapi, {"id": -1, "name": "Twin institute", "directories": None}
    )
    assert org["name"] == "Twin institute"
    assert org["directories"] is None
    # Unknown code, or EDMO unreachable: same
    mocker.patch.object(EDMOFetcher, "get_by_code", return_value=None)
    org = _created_org(
        fastapi, {"id": -1, "name": "Unknown code inst", "directories": "edmo:1"}
    )
    assert org["name"] == "Unknown code inst"
    assert org["directories"] == "edmo:1"


ORGANIZATIONS_EDMO_SEARCH_URL = "/organizations/edmo_search"


def test_organizations_edmo_search(fastapi, mocker):
    search = mocker.patch.object(
        EDMOFetcher,
        "search",
        return_value=[EDMOOrganization(4962, "Sorbonne University")],
    )
    # Needs a logged user
    rsp = fastapi.get(ORGANIZATIONS_EDMO_SEARCH_URL, params={"name": "sorbonne"})
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    search.assert_not_called()
    # Any logged user
    rsp = fastapi.get(
        ORGANIZATIONS_EDMO_SEARCH_URL, headers=USER_AUTH, params={"name": "sorbonne"}
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == [{"code": 4962, "name": "Sorbonne University"}]
    search.assert_called_once_with("sorbonne")


def test_organizations_edmo_search_registration_token(fastapi, mocker, monkeypatch):
    from API_operations.helpers.UserValidation import UserValidation, ActivationType
    from tests.test_users_with_validation import set_config_on

    search = mocker.patch.object(
        EDMOFetcher,
        "search",
        return_value=[EDMOOrganization(4962, "Sorbonne University")],
    )
    params = {"name": "sorbonne", "token": "bogus"}
    # No validation, so no registration token
    rsp = fastapi.get(ORGANIZATIONS_EDMO_SEARCH_URL, params=params)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    set_config_on(monkeypatch)
    # Bad token
    rsp = fastapi.get(ORGANIZATIONS_EDMO_SEARCH_URL, params=params)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    # Token of an existing user, e.g. for modifying a profile, is not a registration one
    validation = UserValidation()
    params["token"] = validation._generate_token(
        "new@plankton.org", id=ORDINARY_USER_USER_ID, action=ActivationType.update.value
    )
    rsp = fastapi.get(ORGANIZATIONS_EDMO_SEARCH_URL, params=params)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    search.assert_not_called()
    # Token sent by email for creating an account
    params["token"] = validation._generate_token(
        "new@plankton.org", action=ActivationType.create.value
    )
    rsp = fastapi.get(ORGANIZATIONS_EDMO_SEARCH_URL, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == [{"code": 4962, "name": "Sorbonne University"}]
    search.assert_called_once_with("sorbonne")
