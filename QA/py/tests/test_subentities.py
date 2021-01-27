# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

import pytest
from API_operations.Consistency import ProjectConsistencyChecker
from API_operations.ObjectManager import ObjectManager
from starlette import status

from tests.test_fastapi import ADMIN_AUTH
from tests.test_import import ADMIN_USER_ID

OUT_JSON = "out.json"
ORIGIN_AFTER_MERGE_JSON = "out_after_merge.json"
SUBS_AFTER_MERGE_JSON = "out_subs_after_merge.json"
OUT_SUBS_JSON = "out_subs.json"
OUT_MERGE_REMAP_JSON = "out_merge_remap.json"


def check_project(prj_id: int):
    problems = ProjectConsistencyChecker(prj_id).run(ADMIN_USER_ID)
    assert problems == []


PROJECT_CHECK_URL = "/projects/{project_id}/check"

OBJECT_QUERY_URL = "/object/{object_id}"
OBJECT_HISTORY_QUERY_URL = "/object/{object_id}/history"
SAMPLE_QUERY_URL = "/sample/{sample_id}"
ACQUISITION_QUERY_URL = "/acquisition/{acquisition_id}"
PROCESS_QUERY_URL = "/process/{process_id}"


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
def test_subentities(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import_uvp6
    prj_id = test_import_uvp6(config, database, caplog, "Test Subset Merge")
    check_project(prj_id)

    # Pick the first object
    qry_rsp, _total = ObjectManager().query(ADMIN_USER_ID, prj_id, filters={})
    first_obj = qry_rsp[0]
    first_objid = first_obj[0]  # obj id

    # Wrong ID
    url = OBJECT_QUERY_URL.format(object_id=-1)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # OK ID
    url = OBJECT_QUERY_URL.format(object_id=first_objid)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    obj = response.json()
    assert obj is not None

    # Move up in hierarchy
    sample_id = first_obj[2]
    # Wrong ID
    url = SAMPLE_QUERY_URL.format(sample_id=-1)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # OK ID
    url = SAMPLE_QUERY_URL.format(sample_id=sample_id)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    sample = response.json()
    assert sample is not None

    acquis_id = first_obj[1]
    # Wrong ID
    url = ACQUISITION_QUERY_URL.format(acquisition_id=-1)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # OK ID
    url = ACQUISITION_QUERY_URL.format(acquisition_id=acquis_id)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    acquisition = response.json()
    assert acquisition is not None

    process_id = acquis_id
    # Wrong ID
    url = PROCESS_QUERY_URL.format(process_id=-1)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # OK ID
    url = PROCESS_QUERY_URL.format(process_id=process_id)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    process = response.json()
    assert process is not None

    # Wrong ID
    url = OBJECT_HISTORY_QUERY_URL.format(object_id=-1)
    response = fastapi.get(url)
    # TODO: A 0-len history should be a not found ?
    #  assert response.status_code == status.HTTP_404_NOT_FOUND
    # OK ID
    url = OBJECT_HISTORY_QUERY_URL.format(object_id=first_objid)
    response = fastapi.get(url)  # The entry point is public and project as well, no need for: , headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    classif = response.json()
    assert classif is not None
    assert len(classif) == 0
