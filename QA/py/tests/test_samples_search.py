# -*- coding: utf-8 -*-
# Searches and stats over several projects check rights on each project,
# but are not an access to them: they must not change the user's recent projects.
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
from tests.test_import import create_project

SAMPLES_SEARCH_URL = "/samples/search?project_ids={project_ids}&id_pattern="
USER_STATS_URL = "/project_set/user_stats?ids={project_ids}"


def _recent_projects(user_id):
    with UserService() as sce:
        prefs = sce.session.get(User, user_id).preferences
    if prefs is None:
        return []
    return json.loads(prefs).get(Preferences.RECENT_PROJECTS_KEY, [])


def test_samples_search_keeps_recent_projects(fastapi):
    # Public projects the user has no right on, readable by any logged user
    prj_ids = [
        create_project(ADMIN_USER_ID, "Samples search %d" % i) for i in range(2)
    ]
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
