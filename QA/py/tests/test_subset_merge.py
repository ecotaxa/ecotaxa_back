# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import logging

from API_models.crud import *
# noinspection PyPackageRequirements
from API_models.merge import MergeRsp
from API_models.subset import SubsetReq
# Import services
# noinspection PyPackageRequirements
from API_operations.CRUD.Projects import ProjectsService
# noinspection PyPackageRequirements
from API_operations.CRUD.Tasks import TaskService
from API_operations.Consistency import ProjectConsistencyChecker
from API_operations.JsonDumper import JsonDumper
from API_operations.Merge import MergeService
from API_operations.Subset import SubsetService
# noinspection PyPackageRequirements
from BO.Mappings import ProjectMapping
# OK we need a bit of direct DB access
# noinspection PyPackageRequirements
from DB import Project, ObjectFields
# noinspection PyPackageRequirements
from deepdiff import DeepDiff
# noinspection PyUnresolvedReferences
from ordered_set import OrderedSet

from tests.test_import import ADMIN_USER_ID, test_import_uvp6

OUT_JSON = "out.json"
ORIGIN_AFTER_MERGE_JSON = "out_after_merge.json"
SUBS_AFTER_MERGE_JSON = "out_subs_after_merge.json"
OUT_SUBS_JSON = "out_subs.json"


def check_project(prj_id: int):
    problems = ProjectConsistencyChecker(prj_id).run(ADMIN_USER_ID)
    assert problems == []


# Note: to go faster in a local dev environment, use "filled_database" instead of "database" below
# BUT DON'T COMMIT THE CHANGE
def test_subset_uvp6(config, database, caplog):
    caplog.set_level(logging.ERROR)
    prj_id = test_import_uvp6(config, database, caplog, "Test Subset Merge")
    check_project(prj_id)
    # Dump the project
    caplog.set_level(logging.DEBUG)
    with open(OUT_JSON, "w") as fd:
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
    SubsetService(prj_id=prj_id, req=params).run(ADMIN_USER_ID)
    # Dump the subset
    with open(OUT_SUBS_JSON, "w") as fd:
        JsonDumper(ADMIN_USER_ID, subset_prj_id, {}).run(fd)

    # Json diff
    with open(OUT_JSON) as fd1:
        json_src = json.load(fd1)
    with open(OUT_SUBS_JSON) as fd2:
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

    # Add a numerical feature into the subset
    session = ProjectsService().session
    prj_bo = session.query(Project).get(subset_prj_id)
    mapg = ProjectMapping().load_from_project(prj_bo)
    mapg.add_column(ObjectFields.__tablename__, "object", "foobar", "n")
    db_col = mapg.search_field("object_foobar")
    assert db_col
    mapg.write_to_project(prj_bo)
    for an_obj in prj_bo.all_objects:
        setattr(an_obj.fields, db_col["field"], 4567)
    session.commit()

    # Re-merge subset into origin project
    # First a dry run to be sure
    does_it_work: MergeRsp = MergeService(prj_id=prj_id, src_prj_id=subset_prj_id, dry_run=True).run(ADMIN_USER_ID)
    assert does_it_work.errors == []
    # Then for real
    does_it_work: MergeRsp = MergeService(prj_id=prj_id, src_prj_id=subset_prj_id, dry_run=False).run(ADMIN_USER_ID)
    assert does_it_work.errors == []

    # The merge introduces duplicates, so below fails
    # check_project(prj_id)

    # Dump the subset which should be just gone
    with open(SUBS_AFTER_MERGE_JSON, "w") as fd:
        JsonDumper(ADMIN_USER_ID, subset_prj_id, {}).run(fd)
    with open(SUBS_AFTER_MERGE_JSON) as fd:
        json_subset = json.load(fd)
    assert json_subset == {}

    # Dump the origin project which should be 2x larger
    with open(ORIGIN_AFTER_MERGE_JSON, "w") as fd:
        JsonDumper(ADMIN_USER_ID, prj_id, {}).run(fd)
    with open(ORIGIN_AFTER_MERGE_JSON) as fd:
        origin_after_merge = json.load(fd)
    # Take the 2nd sample which appeared and compare it with the only one in origin project
    diffs = DeepDiff(json_src["samples"][0], origin_after_merge["samples"][1])
    assert 'iterable_item_added' not in diffs
    assert 'iterable_item_removed' not in diffs
    assert 'dictionary_item_removed' not in diffs
    changed_values = diffs['values_changed']
    # IDs have changed
    del changed_values["root['id']"]  # root is the sample
    del changed_values["root['acquisitions'][0]['id']"]
    del changed_values["root['acquisitions'][0]['processings'][0]['id']"]
    for obj in range(0, 15):
        for img in range(0, 2):
            key = "root['acquisitions'][0]['processings'][0]['objects'][%d]['images'][%d]['fil']" % \
                  (obj, img)
            del changed_values[key]
    assert changed_values == {}
    # New feature appeared
    added_values = diffs['dictionary_item_added']
    for obj in range(0, 15):
        key = "root['acquisitions'][0]['processings'][0]['objects'][%d]['foobar']" % obj
        added_values.remove(key)
    assert added_values == {}


def test_empty_subset_uvp6(config, database, caplog):
    with caplog.at_level(logging.ERROR):
        prj_id = test_import_uvp6(config, database, caplog, "Test empty Subset")

    task_id = TaskService().create()
    subset_prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Empty subset"))
    # OK this test is just for covering the code in filters
    filters: ProjectFilters = {
        "taxo": "23456",
        "taxochild": "Y",
        "statusfilter": "V",
        "MapN": "40",
        "MapW": "45",
        "MapE": "50",
        "MapS": "55",
        "depthmin": "10",
        "depthmax": "40",
        "samples": "1,3,4",
        "instrum": "inst",
        "daytime": "A",
        "month": "5",
        "fromdate": "2020-05-01",
        "todate": "2020-05-31",
        "fromtime": "14:34:01",
        "totime": "15:34",
        "inverttime": "1",
        "validfromdate": "2020-05-01 12:00",
        "validtodate": "2020-05-01 18:00",
        "freenum": "n01",
        "freenumst": "0",
        "freenumend": "999999",
        "freetxt": "p01",
        "freetxtval": "zooprocess",
        "filt_annot": "34,67"
    }
    params = SubsetReq(task_id=task_id,
                       dest_prj_id=subset_prj_id,
                       filters=filters,
                       limit_type='P',
                       limit_value=100.0,
                       do_images=True)
    SubsetService(prj_id=prj_id, req=params).run(ADMIN_USER_ID)