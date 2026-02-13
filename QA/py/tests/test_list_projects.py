# -*- coding: utf-8 -*-
from starlette import status

from tests.credentials import ADMIN_AUTH, USER_AUTH

PROJECTS_URL = "/projects"

# TODO: Create some projects first


def test_list_projects_basic(fastapi):
    # Test as regular user
    rsp = fastapi.get(PROJECTS_URL, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    assert isinstance(results, list)
    if results:
        project = results[0]
        assert "projid" in project
        assert "title" in project


def test_list_projects_admin(fastapi):
    # Test as admin
    rsp = fastapi.get(PROJECTS_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    assert isinstance(results, list)


def test_list_projects_filtering(fastapi):
    # Get all projects first to get some IDs
    rsp = fastapi.get(PROJECTS_URL, headers=ADMIN_AUTH)
    results = rsp.json()
    if len(results) >= 2:
        ids = [str(results[0]["projid"]), str(results[1]["projid"])]
        ids_str = ",".join(ids)

        params = {"project_ids": ids_str}
        rsp = fastapi.get(PROJECTS_URL, headers=ADMIN_AUTH, params=params)
        assert rsp.status_code == status.HTTP_200_OK
        filtered_results = rsp.json()
        assert len(filtered_results) == 2
        returned_ids = [str(p["projid"]) for p in filtered_results]
        for id_ in ids:
            assert id_ in returned_ids


def test_list_projects_pagination(fastapi):
    # Test with window_size=1
    params = {"window_size": 1}
    rsp = fastapi.get(PROJECTS_URL, headers=ADMIN_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    assert len(results) <= 1

    # Test with window_start
    params = {"window_start": 1, "window_size": 1}
    rsp = fastapi.get(PROJECTS_URL, headers=ADMIN_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK


def test_list_projects_for_managing(fastapi):
    params = {"for_managing": True}
    rsp = fastapi.get(PROJECTS_URL, headers=USER_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    results = rsp.json()
    assert isinstance(results, list)
