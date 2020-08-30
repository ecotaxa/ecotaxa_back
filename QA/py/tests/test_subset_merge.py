# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import logging
import sys
from os.path import dirname, realpath
from pathlib import Path
from deepdiff import DeepDiff

import pytest
# noinspection PyPackageRequirements
from API_models.imports import *
from API_models.crud import *
from API_models.subset import SubsetReq, SubsetRsp
# Import services
# noinspection PyPackageRequirements
from API_operations.CRUD.Projects import ProjectsService
# noinspection PyPackageRequirements
from API_operations.CRUD.Tasks import TaskService
# noinspection PyPackageRequirements
from API_operations.imports.Import import ImportAnalysis, RealImport
from API_operations.JsonDumper import JsonDumper
from API_operations.Subset import SubsetService

# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database, filled_database
from tests.test_import import real_params_from_prep_out, ADMIN_USER_ID

DATA_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
V6_FILE = DATA_DIR / "UVP6_example.zip"
V6_DIR = DATA_DIR / "import_uvp6_zip_in_dir"


# Note: to go faster in a local dev, use "filled_database" instead of "database" below
# BUT DON'T COMMIT THE CHANGE
def test_subset_uvp6(config, database, caplog):
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

    # Subset in full, i.e. clone
    task_id = TaskService().create()
    subset_prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Subset of"))
    filters = {"freenum": "n01", "freenumst": "0"}
    params = SubsetReq(task_id=task_id,
                       dest_prj_id=subset_prj_id,
                       filters=filters,
                       limit_type='P',
                       limit_value=100.0,
                       do_images=True)
    SubsetService(prj_id=prj_id, req=params).run()
    # Dump the subset
    with open("out_subs.json", "w") as fd:
        JsonDumper(ADMIN_USER_ID, subset_prj_id, {}).run(fd)

    # Json diff
    with open("out.json") as fd1:
        json_src = json.load(fd1)
    with open("out_subs.json") as fd2:
        json_subset = json.load(fd2)
    diffs = DeepDiff(json_src, json_subset)
    # Validate by removing all know differences b/w source and subset
    assert 'iterable_item_added' not in diffs
    assert 'iterable_item_removed' not in diffs
    assert 'dictionary_item_added' not in diffs
    assert 'dictionary_item_removed' not in diffs
    changed_values = diffs['values_changed']
    # Title is !=
    del changed_values["root['ttl']"]
    # IDs have changed
    del changed_values["root['samples'][0]['id']"]
    del changed_values["root['samples'][0]['acquisitions'][0]['id']"]
    del changed_values["root['samples'][0]['acquisitions'][0]['processings'][0]['id']"]
    for obj in range(0, 15):
        for img in range(0, 2):
            key = "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][%d]['images'][%d]['fil']" % \
                  (obj, img)
            del changed_values[key]
    assert changed_values == {}
