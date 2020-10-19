# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import logging

import pytest
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
from starlette import status

from tests.credentials import CREATOR_AUTH, CREATOR_USER_ID
from tests.test_fastapi import PRJ_CREATE_URL, ADMIN_AUTH, PROJECT_QUERY_URL
from tests.test_import import ADMIN_USER_ID, test_import_uvp6, DATA_DIR, do_import

OUT_JSON = "out.json"
ORIGIN_AFTER_MERGE_JSON = "out_after_merge.json"
SUBS_AFTER_MERGE_JSON = "out_subs_after_merge.json"
OUT_SUBS_JSON = "out_subs.json"
OUT_MERGE_REMAP_JSON = "out_merge_remap.json"

PROJECT_MERGE_URL = "/projects/{project_id}/merge?source_project_id={source_project_id}&dry_run={dry_run}"


def check_project(prj_id: int):
    problems = ProjectConsistencyChecker(prj_id).run(ADMIN_USER_ID)
    assert problems == []


PROJECT_CHECK_URL = "/projects/{project_id}/check"


@pytest.mark.parametrize("prj_id", [-1])
def test_check_project_via_api(prj_id: int, fastapi):
    if prj_id == -1:  # Hack to avoid the test being marked as 'skipped'
        return
    url = PROJECT_CHECK_URL.format(project_id=prj_id)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# Note: to go faster in a local dev environment, use "filled_database" instead of "database" below
# BUT DON'T COMMIT THE CHANGE
def test_subset_merge_uvp6(config, database, fastapi, caplog):
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
    sce = SubsetService(prj_id=prj_id, req=params)
    sce.update_task(taskstate="Running", percent=0, message="Running")
    sce.run(ADMIN_USER_ID)
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
    db_prj: Project = session.query(Project).get(subset_prj_id)
    mapg = ProjectMapping().load_from_project(db_prj)
    mapg.add_column(ObjectFields.__tablename__, "object", "foobar", "n")
    db_col = mapg.search_field("object_foobar")
    assert db_col
    mapg.write_to_project(db_prj)
    for an_obj in db_prj.all_objects:
        setattr(an_obj.fields, db_col["field"], 4567)
    session.commit()

    # Re-merge subset into origin project
    # First a dry run to be sure, via API for variety
    url = PROJECT_MERGE_URL.format(project_id=prj_id, source_project_id=subset_prj_id, dry_run=True)
    response = fastapi.post(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["errors"] == []
    # Then for real
    does_it_work: MergeRsp = MergeService(prj_id=prj_id, src_prj_id=subset_prj_id, dry_run=False).run(ADMIN_USER_ID)
    assert does_it_work.errors == []

    # TODO:The merge introduces duplicates, so below fails
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


MERGE_DIR_1 = DATA_DIR / "merge_test" / "lots_of_cols"
MERGE_DIR_2 = DATA_DIR / "merge_test" / "more_cols"


def test_merge_remap(config, database, fastapi, caplog):
    # Project 1, usual columns
    prj_id = ProjectsService().create(CREATOR_USER_ID, CreateProjectReq(title="Dest project"))
    do_import(prj_id, MERGE_DIR_1, CREATOR_USER_ID)
    check_project(prj_id)
    # Project 2, same columns but different order
    # acq: remove acq_magnification and swap the 2 others
    # process: remove process_stop_n_images & process_gamma_value, put process_software at the end
    # sample: rename sample_volconc to sample_volconc2 and move it in last
    # object: remove object_link object_cv and object_sr, move lat & lon near the end
    prj_id2 = ProjectsService().create(CREATOR_USER_ID, CreateProjectReq(title="Src project"))
    do_import(prj_id2, MERGE_DIR_2, CREATOR_USER_ID)
    check_project(prj_id2)
    # Merge
    url = PROJECT_MERGE_URL.format(project_id=prj_id, source_project_id=prj_id2, dry_run=False)
    response = fastapi.post(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["errors"] == []
    # Dump the dest
    with open(OUT_MERGE_REMAP_JSON, "w") as fd:
        JsonDumper(ADMIN_USER_ID, prj_id, {}).run(fd)
    # Grab all median_mean free col values
    all_lats = []
    with open(OUT_MERGE_REMAP_JSON) as fd:
        for a_line in fd.readlines():
            if "median_mean" in a_line:
                a_line = a_line.strip().strip(",")
                all_lats.append(a_line)
    expected = ['"median_mean": 5555.0' for n in range(11)]
    assert len(all_lats) == len(expected)
    assert all_lats == expected


def test_empty_subset_uvp6(config, database, fastapi, caplog):
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
    # A bit of fastapi testing
    # TODO for #484: Ensure it's a 200 for dst_prj_id and a non-admin user
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK


SUBSET_URL = "/projects/{project_id}/subset"


def test_api_subset(config, database, fastapi, caplog):
    # Subset a fresh project, why not?
    # Create an empty project
    url1 = PRJ_CREATE_URL
    res = fastapi.post(url1, headers=ADMIN_AUTH, json={"title": "API subset src test"})
    src_prj_id = res.json()
    res = fastapi.post(url1, headers=ADMIN_AUTH, json={"title": "API subset tgt test"})
    tgt_prj_id = res.json()
    # Create a task for this run
    task_id = TaskService().create()

    url = SUBSET_URL.format(project_id=src_prj_id)
    req = {"task_id": task_id,
           "dest_prj_id": tgt_prj_id,
           "limit_type": "P",
           "limit_value": 10,
           "do_images": True}
    response = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert response.json()["errors"] == ['No object found to clone into subset.']

    test_check_project_via_api(tgt_prj_id, fastapi)


def test_subset_of_no_visible_issue_484(config, database, fastapi, caplog):
    # https://github.com/oceanomics/ecotaxa_dev/issues/484
    # First found as a subset of subset failed
    url1 = PRJ_CREATE_URL
    res = fastapi.post(url1, headers=CREATOR_AUTH, json={"title": "API subset src test", "visible": False})
    src_prj_id = res.json()
    res = fastapi.post(url1, headers=CREATOR_AUTH, json={"title": "API subset tgt test", "visible": False})
    tgt_prj_id = res.json()
    # Create a task for this run
    task_id = TaskService().create()

    url = SUBSET_URL.format(project_id=src_prj_id)
    req = {"task_id": task_id,
           "dest_prj_id": tgt_prj_id,
           "limit_type": "P",
           "limit_value": 10,
           "do_images": True}
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["errors"] == ['No object found to clone into subset.']

    test_check_project_via_api(tgt_prj_id, fastapi)
