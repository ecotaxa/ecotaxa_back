# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

import pytest
from API_operations.CRUD.Users import UserService

from tests.test_import import ADMIN_USER_ID, create_project


def test_prefs_set_get(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    # Create a dest project
    prj_id = create_project(ADMIN_USER_ID, "Preferences test")
    prefs_for_test = "foo bar boo"
    # Set to something
    with UserService() as sce:
        sce.set_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=prj_id, key="tst", value=prefs_for_test
        )
    # Check it's still there
    with UserService() as sce:
        prefs = sce.get_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=prj_id, key="tst"
        )
        assert prefs == prefs_for_test
        # No error in get if wrong project
        assert "" == sce.get_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=-1, key="tst"
        )
        # No error in get if wrong key
        assert "" == sce.get_preferences_per_project(
            user_id=ADMIN_USER_ID, project_id=prj_id, key="test"
        )
        # Error in set if wrong project
        with pytest.raises(Exception):
            sce.set_preferences_per_project(
                user_id=ADMIN_USER_ID, project_id=-1, key="tst", value="crash!"
            )
