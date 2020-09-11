# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

import pytest
from API_operations.CRUD.Projects import ProjectsService
from API_operations.CRUD.Users import UserService

from tests.test_import import ADMIN_USER_ID, CreateProjectReq


def test_prefs_set_get(config, database, fastapi_noauth, caplog):
    caplog.set_level(logging.ERROR)
    # Create a dest project
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Preferences test"))
    prefs_for_test = "foo bar boo"
    # Set to something
    UserService().set_preferences_per_project(user_id=ADMIN_USER_ID, project_id=prj_id, key="tst",
                                              preference=prefs_for_test)
    # Check it's still there
    prefs = UserService().get_preferences_per_project(user_id=ADMIN_USER_ID, project_id=prj_id, key="tst")
    assert prefs == prefs_for_test
    # No error in get if wrong project
    assert '' == UserService().get_preferences_per_project(user_id=ADMIN_USER_ID, project_id=-1, key="tst")
    # No error in get if wrong key
    assert '' == UserService().get_preferences_per_project(user_id=ADMIN_USER_ID, project_id=prj_id, key="test")
    # Error in set if wrong project
    with pytest.raises(Exception):
        UserService().set_preferences_per_project(user_id=ADMIN_USER_ID, project_id=-1, key="tst", preference="crash!")
