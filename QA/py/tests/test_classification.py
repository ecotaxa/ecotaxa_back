# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

from starlette import status

from tests.credentials import CREATOR_AUTH, ORDINARY_USER2_USER_ID, ADMIN_AUTH
from tests.test_subentities import OBJECT_HISTORY_QUERY_URL

OBJECT_SET_QUERY_URL = "/object_set/{project_id}/query"


def _prj_query(fastapi, auth, prj_id, **kwargs):
    """ Query using the filters in kwargs """
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=auth, json=kwargs)
    obj_ids = rsp.json()["object_ids"]
    return obj_ids


OBJECT_SET_REVERT_URL = "/object_set/{project_id}/revert_to_history?dry_run={dry_run}{tgt_usr}"
OBJECT_SET_RESET_PREDICTED_URL = "/object_set/{project_id}/reset_to_predicted"
OBJECT_SET_CLASSIFY_URL = "/object_set/classify"
OBJECT_SET_DELETE_URL = "/object_set/"


# Note: to go faster in a local dev environment, use "filled_database" instead of "database" below
# BUT DON'T COMMIT THE CHANGE
def test_classif(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import
    prj_id = test_import(config, database, caplog, "Test Classify/Validate")

    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 8

    # Try a revert on a fresh project
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True,
                                       tgt_usr="&target=" + str(ORDINARY_USER2_USER_ID))
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json={})
    # Security barrier
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Working revert, erase all from import - dry first
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    assert len(stats['classif_info']) == 6
    assert len(stats['last_entries']) == 8
    # Working revert, erase all from import
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=False, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    # assert stats == {'classif_info': {}, 'last_entries': []}

    # Reset all to predicted
    url = OBJECT_SET_RESET_PREDICTED_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK

    # Admin (me!) thinks that all is a copepod :)
    def classify_all(classif_id):
        url = OBJECT_SET_CLASSIFY_URL
        classifications = [classif_id for _obj in obj_ids]
        rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"target_ids": obj_ids,
                                                          "classifications": classifications,
                                                          "wanted_qualification": "V"})
        assert rsp.status_code == status.HTTP_200_OK

    copepod_id = 25828
    classify_all(copepod_id)

    # No history yet as the object was just created
    def classif_history():
        url = OBJECT_HISTORY_QUERY_URL.format(object_id=obj_ids[0])
        response = fastapi.get(url, headers=ADMIN_AUTH)
        assert response.status_code == status.HTTP_200_OK
        return response.json()["classif"]

    classif = classif_history()
    assert classif is not None
    assert len(classif) == 0

    # Not a copepod :(
    entomobryomorpha_id = 25835
    classify_all(entomobryomorpha_id)

    classif2 = classif_history()
    assert classif2 is not None
    # Date is not predictable
    classif2[0]['classif_date'] = 'hopefully just now'
    assert classif2 == [{'classif_date': 'hopefully just now',
                         'classif_id': 25828,
                         'classif_qual': 'V',
                         'classif_score': None,
                         'classif_type': 'M',
                         'classif_who': 1,
                         'objid': 1,
                         'taxon_name': 'Copepoda',
                         'user_name': 'Application Administrator'}]

    # There should be 0 predicted
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id, statusfilter='P')
    assert len(obj_ids) == 0
    # There should be 8 validated
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id, statusfilter='V')
    assert len(obj_ids) == 8

    # Delete some object via API, why not?
    rsp = fastapi.delete(OBJECT_SET_DELETE_URL, headers=ADMIN_AUTH, json=obj_ids[:4])
    assert rsp.status_code == status.HTTP_200_OK
