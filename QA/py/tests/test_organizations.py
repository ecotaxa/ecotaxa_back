# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

import pytest
from starlette import status
from tests.credentials import ADMIN_AUTH, USER_AUTH, ORDINARY_USER_USER_ID

ORGANIZATIONS_SEARCH_URL = "/organizations/search"
ORGANIZATIONS_LIST_URL = "/organizations"
ORGANIZATION_CREATE_URL = "/organizations/create"
ORGANIZATION_UPDATE_URL = "/organizations/{organization_id}"


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


def test_organization_create_invalid(fastapi):
    # 1. Create with no name (empty name)
    org_data = {"id": -1, "name": "", "directories": None}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    org_data = {"id": -1, "name": "   ", "directories": None}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # 2. Create with existing name
    # First, create one
    new_org_name = "Duplicate Name Org"
    org_data = {"id": -1, "name": new_org_name, "directories": None}
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_200_OK

    # Try to create another one with same name
    rsp = fastapi.post(ORGANIZATION_CREATE_URL, headers=ADMIN_AUTH, json=org_data)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
