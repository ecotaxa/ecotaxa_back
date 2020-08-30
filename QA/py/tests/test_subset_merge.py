# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


import logging
import sys
from os.path import dirname, realpath
from pathlib import Path

import pytest
# noinspection PyPackageRequirements
from API_models.imports import *
from API_models.crud import *
# Import services
# noinspection PyPackageRequirements
from API_operations.CRUD.Projects import ProjectsService
# noinspection PyPackageRequirements
from API_operations.CRUD.Tasks import TaskService
# noinspection PyPackageRequirements
from API_operations.imports.Import import ImportAnalysis, RealImport
from API_operations.JsonDumper import JsonDumper

# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database, filled_database
from tests.test_import import real_params_from_prep_out, ADMIN_USER_ID

DATA_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
V6_FILE = DATA_DIR / "UVP6_example.zip"
V6_DIR = DATA_DIR / "import_uvp6_zip_in_dir"


def test_import_uvp6(config, database, caplog):
    caplog.set_level(logging.ERROR)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test Subset Merge"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(V6_FILE))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    params = real_params_from_prep_out(task_id, prep_out)
    assert len(prep_out.errors) == 0
    # Do real import
    RealImport(prj_id, params).run()
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    # Dump the project
    caplog.set_level(logging.DEBUG)
    with open("out.json", "w") as fd:
        JsonDumper(ADMIN_USER_ID, prj_id, {}).run(fd)
    print("\n".join(caplog.messages))

