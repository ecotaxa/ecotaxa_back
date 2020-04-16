# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


# Import services
import logging
from os.path import dirname, realpath
from pathlib import Path
from pprint import pprint

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
PLAIN_DIR = DATA_DIR / "import_test"
ISSUES_DIR = DATA_DIR / "import_issues"
EMPTY_DIR = DATA_DIR / "import_issues" / "no_relevant_file"



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
    from tech.AsciiDump import AsciiDumper
    sce = AsciiDumper()
    print("All is in projet #%d, doing dump into %s" % (params["prj"], out_dump))
    sce.run(projid=params["prj"], out=out_dump)


def test_import_again(config, database, caplog):
    """ Re-import into same project """
    caplog.set_level(logging.DEBUG)
    task_sce = TaskService()
    prj_sce = ProjectService()
    # Do step1
    params = {"prj": 1,
              "tsk": task_sce.create(),
              "src": str(PLAIN_DIR),
              "sal": "Y",
              "sod": "Y"}
    step1_out = ImportAnalysis.call(params)
    # Do step2
    params.update(step1_out)
    # Simulate a missing user and map it to admin
    params["fu"]['elizandro rodriguez'] = {'id': 1}
    RealImport.call(params)


def test_import_uvpv6(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()

    params = {"prj": prj_sce.create("Test LS 2"),
              "tsk": task_sce.create(),
              "src": str(V6_FILE),
              "map": {}}
    step1_out = ImportAnalysis.call(params)
    params.update(step1_out)
    # Do step2
    step2_out = RealImport.call(params)


def test_import_empty(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()

    params = {"prj": prj_sce.create("Test LS 4"),
              "tsk": task_sce.create(),
              "src": str(EMPTY_DIR)}
    step1_out = ImportAnalysis.call(params)
    assert len(step1_out["wrn"]) == 1

def test_import_issues(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()

    params = {"prj": prj_sce.create("Test LS 3"),
              "tsk": task_sce.create(),
              "src": str(ISSUES_DIR)}
    step1_out = ImportAnalysis.call(params)
    pprint(step1_out, width=150)

    # Do step2
    # params.update(step1_out)
    # print(params)
    # step2_out = RealImport.call(params)
    # print(step2_out)
