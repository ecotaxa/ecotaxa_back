# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


# Import services
import logging
from os.path import dirname, realpath
from pathlib import Path

from crud.Project import ProjectService
from crud.Task import TaskService
from crud.User import UserService
from tasks.Import import ImportAnalysis, RealImport

# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database

DATA_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
V6_FILE = DATA_DIR / "V6.zip"
PLAIN_FILE = DATA_DIR / "import_test.zip"


def test_import(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()
    user_sce = UserService()
    # Create an admin for mapping
    user_sce.create("admin", "me@home.fr")

    # Do step1
    params = {"prj": prj_sce.create("Test LS"),
              "tsk": task_sce.create(),
              "src": str(PLAIN_FILE)}
    # Mapping for missing taxonomy IDs
    taxo_mapping = {}
    params["map"] = taxo_mapping
    step1_out = ImportAnalysis.call(params)
    # Do step2
    params.update(step1_out)
    # Simulate a missing user and map it to admin
    params["fu"]['elizandro rodriguez'] = {'id': 1}
    print(params)
    step2_out = RealImport.call(params)

    out_dump = "new.txt"
    print("All is in projet #%d, doing dump into %s" % (params["prj"], out_dump))

    from tech.AsciiDump import AsciiDumper
    sce = AsciiDumper()
    sce.run(projid=params["prj"], out=out_dump)


def test_import_uvpv6(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()

    params = {"prj": prj_sce.create("Test LS"),
              "tsk": task_sce.create(),
              "src": str(V6_FILE)}
    # Mapping for missing taxonomy IDs
    taxo_mapping = {}
    params["map"] = taxo_mapping
    step1_out = ImportAnalysis.call(params)
    # Do step2
    params.update(step1_out)
    print(params)
    step2_out = RealImport.call(params)
    print(step2_out)
