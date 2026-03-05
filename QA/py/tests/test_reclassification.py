# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

from starlette import status

from tests.credentials import CREATOR_AUTH, ADMIN_AUTH
from tests.test_classification import (
    query_all_objects,
    get_stats,
    entomobryomorpha_id,
    get_object_classif_history,
    validate_all,
)
from tests.test_import import do_test_import

OBJECT_SET_RECLASSIFY_URL = (
    "/object_set/{project_id}/reclassify?forced_id={forced_id}&reason={reason}"
)

detritus_classif_id = 84963


def reclassify(fastapi, prj_id, from_id, to_id):
    url = OBJECT_SET_RECLASSIFY_URL.format(
        project_id=prj_id, forced_id=to_id, reason="W"
    )
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"taxo": str(from_id)})
    assert rsp.status_code == status.HTTP_200_OK


def test_reclassify_invalid_filters(fastapi):
    prj_id = do_test_import(fastapi, "Test Reclassify Invalid Filters")
    url = OBJECT_SET_RECLASSIFY_URL.format(
        project_id=prj_id, forced_id=entomobryomorpha_id, reason="W"
    )

    invalid_filters = [
        # Multiple taxa
        {"taxo": f"{detritus_classif_id},{entomobryomorpha_id}"},
        # No taxo filter
        {},
        # taxo + other filters
        {"taxo": str(detritus_classif_id), "statusfilter": "V"},
        {"taxo": str(detritus_classif_id), "samples": "123"},
        {"taxo": str(detritus_classif_id), "taxochild": "Y"},
        {"taxo": str(detritus_classif_id), "MapN": "45"},
        {"taxo": str(detritus_classif_id), "MapW": "5"},
        {"taxo": str(detritus_classif_id), "MapE": "10"},
        {"taxo": str(detritus_classif_id), "MapS": "40"},
        {"taxo": str(detritus_classif_id), "depthmin": "0"},
        {"taxo": str(detritus_classif_id), "depthmax": "100"},
        {"taxo": str(detritus_classif_id), "instrum": "uvp5"},
        {"taxo": str(detritus_classif_id), "daytime": "D"},
        {"taxo": str(detritus_classif_id), "month": "1"},
        {"taxo": str(detritus_classif_id), "fromdate": "2020-01-01"},
        {"taxo": str(detritus_classif_id), "todate": "2020-12-31"},
        {"taxo": str(detritus_classif_id), "fromtime": "10:00:00"},
        {"taxo": str(detritus_classif_id), "totime": "12:00:00"},
        {"taxo": str(detritus_classif_id), "inverttime": "1"},
        {"taxo": str(detritus_classif_id), "validfromdate": "2020-01-01 10:00"},
        {"taxo": str(detritus_classif_id), "validtodate": "2020-01-01 12:00"},
        {"taxo": str(detritus_classif_id), "freenum": "n01"},
        {"taxo": str(detritus_classif_id), "freenumst": "0"},
        {"taxo": str(detritus_classif_id), "freenumend": "100"},
        {"taxo": str(detritus_classif_id), "freetxt": "o01"},
        {"taxo": str(detritus_classif_id), "freetxtval": "foo"},
        {"taxo": str(detritus_classif_id), "filt_annot": "1"},
        {"taxo": str(detritus_classif_id), "filt_last_annot": "1"},
    ]

    for filters in invalid_filters:
        rsp = fastapi.post(url, headers=ADMIN_AUTH, json=filters)
        assert (
            rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        ), f"Filters {filters} should have been rejected"


# Simulate change of taxo system, search&replace taxon ref with another
def test_reclassify(fastapi):

    prj_id = do_test_import(fastapi, "Test Reclassify/Validate")

    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 8

    # All is predicted, see source archive. Objects 6 and 7 are detritus.
    # Validate object 6 so we have a mix of states
    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    validate_all(fastapi, obj_ids[6:7], ADMIN_AUTH)
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 7,
        "nb_unclassified": 0,
        "nb_validated": 1,
        "projid": prj_id,
        "used_taxa": [45072, 78418, detritus_classif_id, 85011, 85012, 85078],
    }

    # We have 2 detritus, see original dataset
    obj_ids = query_all_objects(
        fastapi, CREATOR_AUTH, prj_id, taxo=str(detritus_classif_id)
    )
    assert len(obj_ids) == 2
    # but no entomobryomorpha
    no_obj_ids = query_all_objects(
        fastapi, CREATOR_AUTH, prj_id, taxo=str(entomobryomorpha_id)
    )
    assert len(no_obj_ids) == 0

    # Reclassify project from detritus to entomobryomorpha
    reclassify(fastapi, prj_id, detritus_classif_id, entomobryomorpha_id)

    # Stats changed, detritus is gone and entomobryomorpha appeared
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 7,
        "nb_unclassified": 0,
        "nb_validated": 1,
        "projid": prj_id,
        "used_taxa": [
            entomobryomorpha_id,
            45072,
            78418,
            85011,
            85012,
            85078,
        ],
    }

    # Ensure a proper history appeared
    for an_obj in obj_ids:
        classif2 = get_object_classif_history(fastapi, an_obj)
        assert classif2 is not None
        assert classif2[0]["classif_id"] == detritus_classif_id

    # We now have 0 detritus
    obj_ids = query_all_objects(
        fastapi, CREATOR_AUTH, prj_id, taxo=str(detritus_classif_id)
    )
    assert len(obj_ids) == 0
    # and 2 entomobryomorpha
    obj_ids = query_all_objects(
        fastapi, CREATOR_AUTH, prj_id, taxo=str(entomobryomorpha_id)
    )
    assert len(obj_ids) == 2

    # Call usage endpoint for involved taxa
    rsp = fastapi.get(f"/taxon/{detritus_classif_id}/usage", headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert prj_id not in [d["projid"] for d in rsp.json()]

    rsp = fastapi.get(f"/taxon/{entomobryomorpha_id}/usage", headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert prj_id in [d["projid"] for d in rsp.json()]

    # Ensure reclassification history was properly recorded
    rsp = fastapi.get(f"/taxa/reclassification_history/{prj_id}", headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    history = rsp.json()
    assert len(history) > 0
    # Search for the reclassification we just did
    found = False
    for entry in history:
        if entry["from"] == detritus_classif_id and entry["to"] == entomobryomorpha_id:
            found = True
            break
    assert found
