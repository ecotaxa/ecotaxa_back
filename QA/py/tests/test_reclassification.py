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
    classif_history,
    classify_all,
    validate_all,
)

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


# Simulate change of taxo system, search&replace taxon ref with another
def test_reclassif(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import

    prj_id = test_import(database, caplog, "Test Reclassify/Validate")

    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 8

    # All is predicted, see source archive
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 8,
        "nb_unclassified": 0,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [45072, 78418, detritus_classif_id, 85011, 85012, 85078],
    }

    # Validate all as Predicted state cannot mutate
    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    validate_all(fastapi, obj_ids, ADMIN_AUTH)

    # We have 2 detritus, see original dataset
    obj_ids = query_all_objects(
        fastapi, CREATOR_AUTH, prj_id, taxo=str(detritus_classif_id)
    )
    assert len(obj_ids) == 2
    # but no entomobryomorpha
    obj_ids = query_all_objects(
        fastapi, CREATOR_AUTH, prj_id, taxo=str(entomobryomorpha_id)
    )
    assert len(obj_ids) == 0

    # Reclassify them to entomobryomorpha
    reclassify(fastapi, prj_id, detritus_classif_id, entomobryomorpha_id)

    # Stats changed, detritus is gone and entomobryomorpha appeared
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 0,
        "nb_unclassified": 0,
        "nb_validated": 8,
        "projid": prj_id,
        "used_taxa": [entomobryomorpha_id, 45072, 78418, 85011, 85012, 85078],
    }

    # Ensure a proper history appeared
    for an_obj in obj_ids:
        classif2 = classif_history(fastapi, an_obj)
        assert classif2 is not None
        # Date is not predictable
        classif2[0]["classif_date"] = "hopefully just now"
        # nor object_id
        classif2[0]["objid"] = 1
        assert classif2 == [
            {
                "classif_date": "hopefully just now",
                "classif_id": detritus_classif_id,
                "classif_qual": "P",
                "classif_score": None,
                "classif_who": 1,
                "objid": 1,
                "taxon_name": "detritus",
                "user_name": "Application Administrator",
            }
        ]

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
