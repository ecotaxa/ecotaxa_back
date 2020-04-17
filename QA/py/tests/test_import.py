# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


# Import services
import logging
from os.path import dirname, realpath
from pathlib import Path
from pprint import pprint

# noinspection PyPackageRequirements
from crud.Project import ProjectService
# noinspection PyPackageRequirements
from crud.Task import TaskService
# noinspection PyPackageRequirements
from crud.User import UserService
# noinspection PyPackageRequirements
from tasks.Import import ImportAnalysis, RealImport

# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database

DATA_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
V6_FILE = DATA_DIR / "V6.zip"
PLAIN_FILE = DATA_DIR / "import_test.zip"
PLAIN_DIR = DATA_DIR / "import_test"
PLUS_DIR = DATA_DIR / "import_test_plus"
ISSUES_DIR = DATA_DIR / "import_issues" / "tsv_issues"
ISSUES_DIR2 = DATA_DIR / "import_issues" / "no_classif_id"
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
    RealImport.call(params)

    out_dump = "new.txt"
    from tech.AsciiDump import AsciiDumper
    sce = AsciiDumper()
    print("All is in projet #%d, doing dump into %s" % (params["prj"], out_dump))
    sce.run(projid=params["prj"], out=out_dump)


def test_import_again_skipping(config, database, caplog):
    """ Re-import similar files into same project
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_sce = TaskService()
    # Do step1
    params = {"prj": 1,  # <- need the project from first test
              "tsk": task_sce.create(),
              "src": str(PLAIN_FILE),
              "sal": "Y",
              "sod": "Y"}
    step1_out = ImportAnalysis.call(params)
    errs = step1_out["err"]
    found_err = False
    for an_err in errs:
        if "No object to import" in an_err:
            found_err = True
    assert found_err

def test_import_a_bit_more_skipping(config, database, caplog):
    """ Re-import similar files into same project, with an extra one
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_sce = TaskService()
    # Do step1
    params = {"prj": 1,  # <- need the project from first test
              "tsk": task_sce.create(),
              "src": str(PLUS_DIR),
              "sal": "Y",
              "sod": "Y"}
    step1_out = ImportAnalysis.call(params)
    # warns = step1_out["wrn"]
    # found_imps = 0
    # for a_warn in warns:
    #     if "Analyzing file" in a_warn:
    #         found_imps = True
    # # A single TSV should be analyzed
    # assert found_imps == 1
    # Do step2
    params.update(step1_out)
    # Simulate a missing user and map it to admin
    params["fu"]['elizandro rodriguez'] = {'id': 1}
    RealImport.call(params)
    # TODO: Assert the extra "object_extra" in TSV in data/import_test_plus/m106_mn01_n3_sml

def test_import_again_not_skipping_tsv_skipping_imgs(config, database, caplog):
    """ Re-import into same project, not skipping TSVs
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_sce = TaskService()
    # Do step1
    params = {"prj": 1,  # <- need the project from first test
              "tsk": task_sce.create(),
              "src": str(PLAIN_DIR),
              "sal": "N",
              "sod": "Y"}
    step1_out = ImportAnalysis.call(params)
    # Do step2
    params.update(step1_out)
    # Simulate a missing user and map it to admin
    params["fu"]['elizandro rodriguez'] = {'id': 1}
    RealImport.call(params)


def test_import_again_not_skipping_nor_imgs(config, database, caplog):
    """ Re-import into same project, not skipping TSVs or images
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_sce = TaskService()
    # Do step1
    params = {"prj": 1,  # <- need the project from first test
              "tsk": task_sce.create(),
              "src": str(PLAIN_DIR),
              "sal": "N",
              "sod": "N"}
    step1_out = ImportAnalysis.call(params)
    errs = step1_out["err"]
    nb_errs = 0
    for an_err in errs:
        if "Duplicate object" in an_err:
            nb_errs += 1
    assert nb_errs == 11


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
    RealImport.call(params)


def test_import_empty(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()

    params = {"prj": prj_sce.create("Test LS 3"),
              "tsk": task_sce.create(),
              "src": str(EMPTY_DIR)}
    step1_out = ImportAnalysis.call(params)
    assert len(step1_out["err"]) == 1


def test_import_issues(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()

    params = {"prj": prj_sce.create("Test LS 4"),
              "tsk": task_sce.create(),
              "src": str(ISSUES_DIR)}
    step1_out = ImportAnalysis.call(params)
    pprint(step1_out, width=150)

    # Do step2
    # params.update(step1_out)
    # print(params)
    # step2_out = RealImport.call(params)
    # print(step2_out)


def test_import_classif_issue(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_sce = ProjectService()
    task_sce = TaskService()

    params = {"prj": prj_sce.create("Test LS 5"),
              "tsk": task_sce.create(),
              "src": str(ISSUES_DIR2)}
    step1_out = ImportAnalysis.call(params)
    pprint(step1_out, width=150)
    errs = step1_out["err"]
