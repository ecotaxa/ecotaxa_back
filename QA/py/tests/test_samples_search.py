# -*- coding: utf-8 -*-
# Searches and stats over several projects check rights on each project,
# but are not an access to them: they must not change the user's recent projects.
# /samples/search is also a POST with the same parameters in a JSON body (long project lists),
# but they must never be in both the query string and the body.
import json

from starlette import status

from API_operations.CRUD.ObjectParents import SamplesService
from API_operations.CRUD.Projects import ProjectsService
from API_operations.CRUD.Users import UserService
from BO.DataLicense import AccessLevelEnum
from BO.Preferences import Preferences
from DB.ProjectPrivilege import ProjectPrivilege
from DB.User import User
from tests.credentials import (
    ADMIN_USER_ID,
    ADMIN_AUTH,
    USER_AUTH,
    ORDINARY_USER_USER_ID,
)
from tests.test_import import create_project, do_test_import
from tests.test_project_bo_set import _counting_queries

SAMPLES_SEARCH_URL = "/samples/search?project_ids={project_ids}&id_pattern="
SAMPLES_SEARCH_POST_URL = "/samples/search"
USER_STATS_URL = "/project_set/user_stats?ids={project_ids}"


def _recent_projects(user_id):
    with UserService() as sce:
        prefs = sce.session.get(User, user_id).preferences
    if prefs is None:
        return []
    return json.loads(prefs).get(Preferences.RECENT_PROJECTS_KEY, [])


def test_samples_search_keeps_recent_projects(fastapi):
    # Public projects the user has no right on, readable by any logged user
    prj_ids = [create_project(ADMIN_USER_ID, "Samples search %d" % i) for i in range(2)]
    before = _recent_projects(ORDINARY_USER_USER_ID)
    url = SAMPLES_SEARCH_URL.format(project_ids=",".join(str(p) for p in prj_ids))
    rsp = fastapi.get(url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == []
    # A search is not an access to each project: recent projects unchanged
    assert _recent_projects(ORDINARY_USER_USER_ID) == before


def test_user_stats_keeps_recent_projects(fastapi):
    # Admin reading users stats of several projects, e.g. a collection's ones
    prj_ids = [create_project(ADMIN_USER_ID, "User stats %d" % i) for i in range(2)]
    before = _recent_projects(ADMIN_USER_ID)
    url = USER_STATS_URL.format(project_ids=",".join(str(p) for p in prj_ids))
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert _recent_projects(ADMIN_USER_ID) == before


def test_samples_search_post(fastapi):
    # Long project lists can be sent in the body, same result as GET
    prj_ids = [do_test_import(fastapi, "Samples search POST %d" % i) for i in range(2)]
    ids_str = ",".join(str(p) for p in prj_ids)
    rsp = fastapi.get(
        SAMPLES_SEARCH_URL.format(project_ids=ids_str), headers=ADMIN_AUTH
    )
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
            "'%s' given both in query string and body" % a_param in rsp.json()["detail"]
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


# Rights over many projects are checked in one go, with the same answers as one by one
PRIVATE = AccessLevelEnum.PRIVATE.value
PUBLIC = AccessLevelEnum.PUBLIC.value
OPEN = AccessLevelEnum.OPEN.value


def _search(fastapi, prj_ids, auth):
    ids = ",".join(str(p) for p in prj_ids)
    return fastapi.get(SAMPLES_SEARCH_URL.format(project_ids=ids), headers=auth)


def _grant(prj_id, user_id, privilege):
    with ProjectsService() as sce:
        priv = ProjectPrivilege()
        priv.projid = prj_id
        priv.member = user_id
        priv.privilege = privilege
        sce.session.add(priv)
        sce.session.commit()


def test_samples_search_rights_on_many_projects(fastapi):
    public = create_project(ADMIN_USER_ID, "Samples rights public", access=PUBLIC)
    an_open = create_project(ADMIN_USER_ID, "Samples rights open", access=OPEN)
    private = create_project(ADMIN_USER_ID, "Samples rights private", access=PRIVATE)
    viewed = create_project(ADMIN_USER_ID, "Samples rights viewed", access=PRIVATE)
    _grant(viewed, ORDINARY_USER_USER_ID, "View")
    unknown = 999999
    ok, refused, not_found = (
        status.HTTP_200_OK,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    )
    # Logged user: public, open, and private with a privilege are readable
    assert _search(fastapi, [public, an_open, viewed], USER_AUTH).status_code == ok
    # One private project in the list, wherever it is, refuses all
    assert _search(fastapi, [public, private], USER_AUTH).status_code == refused
    assert _search(fastapi, [private, public], USER_AUTH).status_code == refused
    # Unknown project
    assert _search(fastapi, [public, unknown], USER_AUTH).status_code == not_found
    # First failure in list order wins, as when checking one by one
    assert _search(fastapi, [unknown, private], USER_AUTH).status_code == not_found
    assert _search(fastapi, [private, unknown], USER_AUTH).status_code == refused
    # Admin reads anything existing
    assert _search(fastapi, [private, public], ADMIN_AUTH).status_code == ok
    assert _search(fastapi, [private, unknown], ADMIN_AUTH).status_code == not_found
    # Anonymous: only open projects, unknown ones are refused
    assert _search(fastapi, [an_open], {}).status_code == ok
    assert _search(fastapi, [an_open, public], {}).status_code == refused
    assert _search(fastapi, [an_open, unknown], {}).status_code == refused
    # Duplicates and empty list
    assert _search(fastapi, [public, public], USER_AUTH).json() == []
    assert _search(fastapi, [], USER_AUTH).json() == []


def test_samples_search_rights_in_constant_queries(database):
    prj_ids = [
        create_project(ADMIN_USER_ID, "Samples rights queries %d" % i) for i in range(6)
    ]
    counts = []
    for some_ids in (prj_ids[:2], prj_ids):
        with SamplesService() as sce:
            with _counting_queries(sce.session) as statements:
                sce.search(ORDINARY_USER_USER_ID, some_ids, "")
            # The background job scheduler polls on the same engine, at any time
            mine = [a_stmt for a_stmt in statements if "FROM job" not in a_stmt]
            counts.append(len(mine))
    assert counts[0] == counts[1], counts
