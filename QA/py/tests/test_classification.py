# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

from starlette import status

from tests.credentials import CREATOR_AUTH, ORDINARY_USER2_USER_ID, ADMIN_AUTH
from tests.test_import import test_import

OBJECT_SET_QUERY_URL = "/object_set/{project_id}/query"
OBJECT_SET_REVERT_URL = "/object_set/{project_id}/revert_to_history?dry_run={dry_run}&target={tgt_usr}"
OBJECT_SET_RESET_PREDICTED_URL = "/object_set/{project_id}/reset_to_predicted"
OBJECT_SET_CLASSIFY_URL = "/object_set/classify"


def _prj_query(fastapi, auth, prj_id, **kwargs):
    """ Query using the filters in kwargs """
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=auth, json=kwargs)
    obj_ids = rsp.json()["object_ids"]
    return obj_ids

# Note: to go faster in a local dev environment, use "filled_database" instead of "database" below
# BUT DON'T COMMIT THE CHANGE
def test_classif(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    prj_id = test_import(config, database, caplog, "Test Classify/Validate")

    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 8

    # Try a revert on a fresh project
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True, tgt_usr=ORDINARY_USER2_USER_ID)
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json={})
    # Security barrier
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Working revert
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True, tgt_usr=ORDINARY_USER2_USER_ID)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    assert stats == {'classif_info': {}, 'last_entries': []}

    # Reset all to predicted
    url = OBJECT_SET_RESET_PREDICTED_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK

    # Admin (me!) thinks that all is a copepod :)
    url = OBJECT_SET_CLASSIFY_URL
    copepod_id = 45072  # TODO: Not a copepod :( but in DB
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"target_ids": obj_ids,
                                                      "classifications": [copepod_id for _obj in obj_ids],
                                                      "wanted_qualification": "V"})
    assert rsp.status_code == status.HTTP_200_OK

    # There should be 0 predicted
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id, statusfilter='P')
    assert len(obj_ids) == 0
    # There should be 8 validated
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id, statusfilter='V')
    assert len(obj_ids) == 8
