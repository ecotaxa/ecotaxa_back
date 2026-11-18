# -*- coding: utf-8 -*-
# /samples/search, GET with query string or POST with the same parameters in a JSON body
# (for long project lists), but never in both places.
import json

from starlette import status

from API_operations.CRUD.Users import UserService
from BO.Preferences import Preferences
from DB.User import User
from tests.credentials import (
    ADMIN_USER_ID,
    ADMIN_AUTH,
    USER_AUTH,
    ORDINARY_USER_USER_ID,
)
from tests.test_import import create_project, do_test_import

SAMPLES_SEARCH_URL = "/samples/search?project_ids={project_ids}&id_pattern="
SAMPLES_SEARCH_POST_URL = "/samples/search"


def _recent_projects(user_id):
    with UserService() as sce:
        prefs = sce.session.get(User, user_id).preferences
    if prefs is None:
        return []
    return json.loads(prefs).get(Preferences.RECENT_PROJECTS_KEY, [])


def test_samples_search_post(fastapi):
    # Long project lists can be sent in the body, same result as GET
    prj_ids = [do_test_import(fastapi, "Samples search POST %d" % i) for i in range(2)]
    ids_str = ",".join(str(p) for p in prj_ids)
    rsp = fastapi.get(SAMPLES_SEARCH_URL.format(project_ids=ids_str), headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    in_get = rsp.json()
    assert len(in_get) > 0
    assert {a_sam["projid"] for a_sam in in_get} == set(prj_ids)
    rsp = fastapi.post(
        SAMPLES_SEARCH_POST_URL,
        headers=ADMIN_AUTH,
        json={"project_ids": ids_str, "id_pattern": "*"},
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == in_get
    # id_pattern defaults to 'any'
    rsp = fastapi.post(
        SAMPLES_SEARCH_POST_URL, headers=ADMIN_AUTH, json={"project_ids": ids_str}
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == in_get
    # A pattern matching nothing
    rsp = fastapi.post(
        SAMPLES_SEARCH_POST_URL,
        headers=ADMIN_AUTH,
        json={"project_ids": ids_str, "id_pattern": "no_such_sample_xyz"},
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == []


def test_samples_search_post_refuses_both_places(fastapi):
    prj_id = create_project(ADMIN_USER_ID, "Samples search POST both places")
    for a_param, a_val in (("project_ids", prj_id), ("id_pattern", "*")):
        rsp = fastapi.post(
            SAMPLES_SEARCH_POST_URL + "?%s=%s" % (a_param, a_val),
            headers=ADMIN_AUTH,
            json={"project_ids": str(prj_id)},
        )
        assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert (
            "'%s' given both in query string and body" % a_param
            in rsp.json()["detail"]
        )


def test_samples_search_post_keeps_recent_projects(fastapi):
    # Public projects the user has no right on, readable by any logged user
    prj_ids = [
        create_project(ADMIN_USER_ID, "Samples search POST recent %d" % i)
        for i in range(2)
    ]
    before = _recent_projects(ORDINARY_USER_USER_ID)
    rsp = fastapi.post(
        SAMPLES_SEARCH_POST_URL,
        headers=USER_AUTH,
        json={"project_ids": ",".join(str(p) for p in prj_ids)},
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == []
    # A search is not an access to each project: recent projects unchanged
    assert _recent_projects(ORDINARY_USER_USER_ID) == before
