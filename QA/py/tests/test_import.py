# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database

# Import services
from crud.Project import ProjectService
from crud.Task import TaskService
from tasks.ImportStep1 import ImportStep1
from tasks.ImportStep2 import ImportStep2



def test_import(config, database):
    prj_sce = ProjectService()
    task_sce = TaskService()

    # Do step1
    sce1 = ImportStep1()
    sce1.prj_id = prj_sce.create("Test LS")
    sce1.task_id = task_sce.create()
    sce1.input_path = "../data/V6.zip"
    sce1.run()
    # Do step2
    sce2 = ImportStep2()
    sce2.mapping = sce1.mapping
    sce2.prj_id = sce1.prj_id
    sce2.task_id = sce1.task_id
    sce2.source_dir_or_zip = sce1.source_dir_or_zip
    # Map to admin
    sce2.found_users['elizandro rodriguez'] = {'id': 1}
    sce2.run()

    out_dump = "new.txt"
    print("All is in projet #%d, doing dump into %s" % (sce2.prj_id, out_dump))

    from tech.AsciiDump import AsciiDumper
    sce = AsciiDumper()
    sce.run(projid=sce2.prj_id, out=out_dump)
