# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


# Import services
from os.path import dirname, realpath
from pathlib import Path

from crud.Project import ProjectService
from crud.Task import TaskService
from crud.User import UserService
from tasks.ImportStep1 import ImportStep1
from tasks.ImportStep2 import ImportStep2

# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database

DATA_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
V6_FILE = DATA_DIR / "V6.zip"
PLAIN_FILE = DATA_DIR / "import_test.zip"


def test_import(config, database):
    prj_sce = ProjectService()
    task_sce = TaskService()
    user_sce = UserService()
    # Create an admin for mapping
    user_sce.create("admin", "me@home.fr")

    # Do step1
    sce1 = ImportStep1()
    sce1.prj_id = prj_sce.create("Test LS")
    sce1.task_id = task_sce.create()
    sce1.input_path = str(PLAIN_FILE)
    step1_out = sce1.run()
    # Serialize output
    # Do step2
    sce2 = ImportStep2(step1_out)
    # Map to admin
    sce2.found_users['elizandro rodriguez'] = {'id': 1}
    sce2.run()

    out_dump = "new.txt"
    print("All is in projet #%d, doing dump into %s" % (sce2.prj_id, out_dump))

    from tech.AsciiDump import AsciiDumper
    sce = AsciiDumper()
    sce.run(projid=sce2.prj_id, out=out_dump)
