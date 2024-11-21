# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
from typing import List

import pytest
from API_models.filters import ProjectFiltersDict
from API_operations.helpers.Service import Service
from DB.Prediction import Prediction, PredictionHisto
from DB.helpers import Result
from DB.helpers.Core import select
from DB.helpers.ORM import any_
from sqlalchemy import text
from starlette import status

from tests.credentials import (
    CREATOR_AUTH,
    ORDINARY_USER2_USER_ID,
    ADMIN_AUTH,
    CREATOR_USER_ID,
)
from tests.test_import import VARIOUS_STATES_DIR, create_project, import_various
from tests.credentials import CREATOR_AUTH, ORDINARY_USER2_USER_ID, ADMIN_AUTH
from tests.prj_utils import sce_check_consistency
from tests.test_import import VARIOUS_STATES_DIR
from tests.test_objectset_query import OBJECT_SET_QUERY_URL
from tests.test_prj_admin import PROJECT_CLASSIF_STATS_URL
from tests.test_subentities import OBJECT_HISTORY_QUERY_URL
from tests.test_taxa_query import TAXA_SET_QUERY_URL


def query_all_objects(fastapi, auth, prj_id, **kwargs) -> List[int]:
    """Query using the filters in kwargs,return the full list of object IDs, sorted for stability"""
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=auth, json=kwargs)
    obj_ids = rsp.json()["object_ids"]
    return sorted(obj_ids)


OBJECT_SET_REVERT_URL = (
    "/object_set/{project_id}/revert_to_history?dry_run={dry_run}{tgt_usr}"
)
OBJECT_SET_RESET_PREDICTED_URL = "/object_set/{project_id}/reset_to_predicted"
OBJECT_SET_CLASSIFY_URL = "/object_set/classify"
OBJECT_SET_GET_PREDICTION_INFO_URL = "/object_set/predictions"
OBJECT_SET_CLASSIFY_AUTO_URL = "/object_set/classify_auto"
OBJECT_SET_CLASSIFY_AUTO_URL2 = "/object_set/classify_auto_multiple"
OBJECT_SET_DELETE_URL = "/object_set/"
OBJECT_SET_SUMMARY_URL = "/object_set/{project_id}/summary?only_total=False"
OBJECT_SET_PARENTS_URL = "/object_set/parents"
OBJECT_QUERY_URL = "/object/{object_id}"

PROJECT_SET_USER_STATS = "/project_set/user_stats?ids={prj_ids}"

copepod_id = 25828
entomobryomorpha_id = 25835
crustacea_id = 12846
minidiscus_id = 28234


def get_classif_history(fastapi, object_id):
    url = OBJECT_HISTORY_QUERY_URL.format(object_id=object_id)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    return response.json()


def get_stats(fastapi, prj_id):
    stats_url = PROJECT_CLASSIF_STATS_URL.format(prj_ids="%s" % prj_id)
    stats_rsp = fastapi.get(stats_url, headers=ADMIN_AUTH)
    assert stats_rsp.status_code == status.HTTP_200_OK
    return stats_rsp.json()[0]


def get_project_stats(fastapi, prj_id):
    stats_url = OBJECT_SET_SUMMARY_URL.format(project_id=prj_id)
    filters = ProjectFiltersDict()
    stats_rsp = fastapi.post(stats_url, headers=ADMIN_AUTH, json=filters)
    assert stats_rsp.status_code == status.HTTP_200_OK
    return stats_rsp.json()


def get_predictions_stats(obj_ids):
    with Service() as sce:
        qry = select(
            Prediction.object_id, Prediction.training_id, text("'P' as chk")
        )  # TODO: makes sense to update this
        qry = qry.where(Prediction.object_id == any_(obj_ids))
        qry2 = select(
            PredictionHisto.object_id, PredictionHisto.training_id, text("'H' as chk")
        )  # TODO: makes sense to update this
        qry2 = qry2.where(PredictionHisto.object_id == any_(obj_ids))
        qry = qry.union_all(qry2)
        # print("***", obj_ids, file=stderr)
        res: Result = sce.session.execute(qry)
        pred_stats = {
            "n_trainings": 0,
            "n_objects_in_predictions": 0,
            "n_predictions": 0,
            "n_predictions_h": 0,
            "n_discarded": 0,
        }
        pred_objects = list()
        trainings = set()
        for rec in res.fetchall():
            # print(rec, file=stderr)
            if rec["object_id"] not in pred_objects:
                pred_objects.append(rec["object_id"])
                pred_stats["n_objects_in_predictions"] += 1
            if rec["chk"] == "P":
                pred_stats["n_predictions"] += 1
            else:
                pred_stats["n_predictions_h"] += 1
            trainings.add(rec["training_id"])
        pred_stats["n_trainings"] = len(trainings)
        # if rec["discarded"]:
        #     pred_stats["n_discarded"] += 1
    return pred_stats


def get_prediction_infos(fastapi, obj_ids, who=ADMIN_AUTH):
    url = OBJECT_SET_GET_PREDICTION_INFO_URL
    rsp = fastapi.post(url, headers=who, json=obj_ids)
    assert rsp.status_code == status.HTTP_200_OK
    return rsp.json()


def classify_all(fastapi, obj_ids, classif_id, who=ADMIN_AUTH):
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [classif_id for _obj in obj_ids]
    rsp = fastapi.post(
        url,
        headers=who,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK


def classify_all_no_change(fastapi, obj_ids):
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK


def validate_all(fastapi, obj_ids, who=ADMIN_AUTH):
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]
    rsp = fastapi.post(
        url,
        headers=who,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK


def classify_all_no_change(fastapi, obj_ids):
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK


def validate_all(fastapi, obj_ids, who=ADMIN_AUTH):
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]
    rsp = fastapi.post(
        url,
        headers=who,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK


def classify_auto_mult_all(fastapi, obj_ids, classif_id, scores):
    url = OBJECT_SET_CLASSIFY_AUTO_URL2
    classifications = [classif_id for _obj in obj_ids]
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "scores": scores,
            "keep_log": True,
        },
    )
    assert rsp.status_code == status.HTTP_200_OK


def classify_auto_incorrect(fastapi, obj_ids):
    url = OBJECT_SET_CLASSIFY_AUTO_URL2
    n = 3
    classifications = [[-1] * n for _obj in obj_ids]

    # List of scores of a different length, should raise an error
    scores = [[0.1] * n for _obj in obj_ids[:-1]]
    with pytest.raises(AssertionError):
        rsp = fastapi.post(
            url,
            headers=ADMIN_AUTH,
            json={
                "target_ids": obj_ids,
                "classifications": classifications,
                "scores": scores,
                "keep_log": True,
            },
        )
    # List of scores outside [0, 1], should raise an error
    scores = [[2.0] * n for _obj in obj_ids]
    with pytest.raises(AssertionError):
        rsp = fastapi.post(
            url,
            headers=ADMIN_AUTH,
            json={
                "target_ids": obj_ids,
                "classifications": classifications,
                "scores": scores,
                "keep_log": True,
            },
        )
    # List of scores with wrong type, should fail
    scores = [[None] * n for _obj in obj_ids]
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "scores": scores,
            "keep_log": True,
        },
    )
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Note: to go faster in a local dev environment, use "filled_database" instead of "database" below
# BUT DON'T COMMIT THE CHANGE
def test_classif(database, fastapi, caplog, tstlogs):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import

    prj_id = test_import(
        database, caplog, "Test Classify/Validate", path=str(VARIOUS_STATES_DIR)
    )
    sce_check_consistency("start")

    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 9

    # See if the taxa we are going to use are OK
    rsp = fastapi.get(
        TAXA_SET_QUERY_URL.format(taxa_ids="%d+%d" % (copepod_id, entomobryomorpha_id))
    )
    # Note: There is no real lineage in test DB
    assert rsp.json() == [
        {
            "children": [84964],
            "display_name": "Copepoda",
            "id": copepod_id,
            "id_lineage": [copepod_id, 16621, 12846, 11517, 2367, 382, 8, 2, 1],
            "lineage": [
                "Copepoda",
                "Maxillopoda",
                "Crustacea",
                "Arthropoda",
                "Metazoa",
                "Holozoa",
                "Opisthokonta",
                "Eukaryota",
                "living",
            ],
            "name": "Copepoda",
            "nb_children_objects": 0,
            "nb_objects": 0,
            "renm_id": None,
            "type": "P",
        },
        {
            "children": [],
            "display_name": "Entomobryomorpha",
            "id": 25835,
            "id_lineage": [25835, 16630, 12845, 11517, 2367, 382, 8, 2, 1],
            "lineage": [
                "Entomobryomorpha",
                "Collembola",
                "Hexapoda",
                "Arthropoda",
                "Metazoa",
                "Holozoa",
                "Opisthokonta",
                "Eukaryota",
                "living",
            ],
            "name": "Entomobryomorpha",
            "nb_children_objects": 0,
            "nb_objects": 0,
            "renm_id": None,
            "type": "P",
        },
    ]

    # Initial stats just after load

    # We have a like-in-real-life mix of states
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 1,
        "nb_predicted": 3,  # counting from 1: objects 1,4,6 see TSVs
        "nb_unclassified": 1,
        "nb_validated": 4,
        "projid": prj_id,
        "used_taxa": [-1, 45072, 78418, 84963, 85011, 85012, 85078],
    }

    assert get_predictions_stats(obj_ids) == {
        "n_trainings": 1,  # import creates a pseudo-prediction
        "n_objects_in_predictions": 3,
        "n_predictions": 3,  # single score for each of the 3 predicted objects
        "n_predictions_h": 0,
        "n_discarded": 0,
    }

    # Try a revert on a fresh project

    # Not working due to permissions
    url = OBJECT_SET_REVERT_URL.format(
        project_id=prj_id,
        dry_run=True,
        tgt_usr="&target=" + str(ORDINARY_USER2_USER_ID),
    )
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json={})
    # Security barrier
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Working revert, erase all from import - dry first
    stats = dry_run_revert(fastapi, prj_id)
    assert len(stats["classif_info"]) == 6
    assert len(stats["last_entries"]) == 9
    # Working revert, erase all from import
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=False, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    assert stats["classif_info"] == {}  # Nothing is classified anymore

    # Same stats
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 0,
        "nb_unclassified": 9,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [-1],
    }

    obj_stats = get_project_stats(fastapi, prj_id)
    assert obj_stats == {
        "dubious_objects": 0,
        "predicted_objects": 0,
        "total_objects": 9,
        "validated_objects": 0,
    }

    no_pred_stats = {
        "n_trainings": 0,  # we still have the import training, but it's now empty
        "n_predictions": 0,
        "n_predictions_h": 0,
        "n_objects_in_predictions": 0,
        "n_discarded": 0,
    }
    assert get_predictions_stats(obj_ids) == no_pred_stats

    sce_check_consistency("after revert on fresh")

    # Reset (force) all to predicted. This does nothing as no objet is in target state (dubious or validated)
    url = OBJECT_SET_RESET_PREDICTED_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK

    assert get_predictions_stats(obj_ids) == no_pred_stats

    sce_check_consistency("after force predicted")

    # Incorrect ML results
    classify_auto_incorrect(fastapi, obj_ids[:4])

    assert get_predictions_stats(obj_ids) == no_pred_stats

    sce_check_consistency("after incorrect auto classify")

    # Multiple ML result, 4 first objects are crustacea/copepod/entomobryomorpha with same scores
    classify_auto_mult_all(
        fastapi,
        obj_ids[:4],
        [crustacea_id, copepod_id, entomobryomorpha_id],
        [[0.52, 0.2, 0.08]] * 4,
    )

    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 4,
        "nb_unclassified": 5,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [-1, crustacea_id],
    }

    assert get_predictions_stats(obj_ids) == {
        "n_trainings": 1,  # call to classify_auto_mult added 1
        "n_predictions": 12,  # 4 objects * 3 score
        "n_predictions_h": 0,  # no histo
        "n_objects_in_predictions": 4,  # #1,2,3,4
        "n_discarded": 0,
    }

    sce_check_consistency("after classif auto")

    # New ML results with a different score for the second object
    classify_auto_mult_all(
        fastapi,
        [obj_ids[1]],
        [crustacea_id, copepod_id, entomobryomorpha_id],
        [[0.8, 0.1, 0.05]],
    )
    url = OBJECT_QUERY_URL.format(object_id=obj_ids[1])
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    # assert rsp.json()["classif_auto_score"] == 0.8

    obj_stats_after_prediction = {
        "nb_dubious": 0,
        "nb_predicted": 4,
        "nb_unclassified": 5,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [-1, crustacea_id],
    }
    assert get_stats(fastapi, prj_id) == obj_stats_after_prediction

    pred_stats_after_second_prediction = {
        "n_trainings": 2,  # call to classify_auto_mult added 1
        "n_objects_in_predictions": 4,
        "n_predictions": 12,  # Still 4 objects * 3 scores
        "n_predictions_h": 3,  # previous prediction historized for the double-predicted one
        "n_discarded": 0,
    }
    assert get_predictions_stats(obj_ids) == pred_stats_after_second_prediction

    obj_one = obj_ids[1]
    assert get_prediction_infos(fastapi, [obj_one]) == {
        "result": [
            [obj_one, crustacea_id, 0.8],
            [obj_one, copepod_id, 0.1],
            [obj_one, entomobryomorpha_id, 0.05],
        ]
    }
    # Still same stats but obj_one now has a stack of 2 predictions
    obj_stats_after_second_prediction = {
        "nb_dubious": 0,
        "nb_predicted": 4,
        "nb_unclassified": 4,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [-1, crustacea_id],
    }
    assert get_stats(fastapi, prj_id) == obj_stats_after_second_prediction

    sce_check_consistency("after classif auto obj1")

    # Admin (me!) thinks that all is a minidiscus, regardless of ML advices
    classify_all(fastapi, obj_ids, minidiscus_id)

    # Same stats
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 0,
        "nb_unclassified": 0,
        "nb_validated": 9,
        "projid": prj_id,
        "used_taxa": [minidiscus_id],
    }  # No more Unclassified (-1) and Minidiscus is in +

    # No change here
    assert get_predictions_stats(obj_ids) == {
        "n_discarded": 0,
        "n_objects_in_predictions": 4,
        "n_predictions": 0,
        "n_predictions_h": 15,  # All in history
        "n_trainings": 2,
    }

    # Check history for first object
    classif = get_classif_history(fastapi, obj_ids[0])
    assert len(classif) == 1
    assert classif[0]["classif_date"] is not None  # e.g. 2021-09-12T09:28:03.278626
    classif[0]["classif_date"] = "now"
    assert classif == [
        {
            "objid": obj_ids[0],
            "classif_id": crustacea_id,
            "classif_date": "now",
            "classif_who": None,
            "classif_qual": "P",
            "classif_type": "A",
            "classif_score": 0.52,  # Highest score
            "user_name": None,
            "taxon_name": "Crustacea",
        }
    ]

    sce_check_consistency("inside")

    # Move all to minidiscus was NOK, rollback
    revert_url = OBJECT_SET_REVERT_URL.format(
        project_id=prj_id, dry_run=False, tgt_usr=""
    )
    rsp = fastapi.post(revert_url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()

    assert get_stats(fastapi, prj_id) == obj_stats_after_prediction
    assert get_predictions_stats(obj_ids) == pred_stats_after_second_prediction

    sce_check_consistency("revert")

    # Second revert
    stats = dry_run_revert(fastapi, prj_id)
    rsp = fastapi.post(revert_url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()

    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 1,  # 3 predicted objects lost their whole history, 1 remains as it was predicted twice
        "nb_unclassified": 7,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [-1, 12846],
    }
    pred_stats_after_second_revert = {
        "n_trainings": 1,
        "n_objects_in_predictions": 1,
        "n_predictions": 3,
        "n_predictions_h": 0,
        "n_discarded": 0,
    }
    assert get_predictions_stats(obj_ids) == pred_stats_after_second_revert

    sce_check_consistency("second revert")

    # Apply validation again after revert
    classify_all(fastapi, obj_ids, copepod_id)

    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 0,
        "nb_unclassified": 0,
        "nb_validated": 8,
        "projid": prj_id,
        "used_taxa": [copepod_id],
    }
    pred_stats_after_classify_all = {
        "n_trainings": 1,
        "n_objects_in_predictions": 1,
        "n_predictions": 0,
        "n_predictions_h": 3,
        "n_discarded": 0,
    }
    assert get_predictions_stats(obj_ids) == pred_stats_after_classify_all

    sce_check_consistency("classify after revert")

    # Not a copepod :(
    classify_all(fastapi, obj_ids, entomobryomorpha_id)

    sce_check_consistency("classify all after revert")

    classify_all_no_change(fastapi, obj_ids)

    # Nothing new on prediction side
    assert get_predictions_stats(obj_ids) == pred_stats_after_classify_all

    # History stack of twice-predicted object, once rolled-back object
    classif2 = get_classif_history(fastapi, obj_ids[1])
    assert classif2 is not None
    # Date is not predictable
    classif2[0]["classif_date"] = "hopefully just now"
    classif2[1]["classif_date"] = "a bit before"
    assert classif2 == [
        {
            "classif_date": "hopefully just now",
            "classif_id": copepod_id,
            "classif_qual": "V",
            # "classif_score": 0.2, # TODO: show or not?
            "classif_type": "M",
            "classif_score": None,
            "classif_who": 1,
            "objid": obj_ids[1],
            "taxon_name": "Copepoda",
            "user_name": "Application Administrator",
        },
        {
            "classif_date": "a bit before",
            "classif_id": crustacea_id,
            "classif_qual": "P",
            "classif_type": "A",
            "classif_score": 0.52,
            "classif_who": None,
            "objid": obj_ids[1],
            "taxon_name": "Crustacea",
            "user_name": None,
        },
    ]

    # There should be 0 predicted
    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id, statusfilter="P")
    assert len(obj_ids) == 0
    # There should be 8 validated
    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id, statusfilter="V")
    assert len(obj_ids) == 9

    url = PROJECT_CLASSIF_STATS_URL.format(prj_ids="%s" % prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == [
        {
            "nb_dubious": 0,
            "nb_predicted": 0,
            "nb_unclassified": 0,
            "nb_validated": 9,
            "projid": prj_id,
            "used_taxa": [
                entomobryomorpha_id
            ],  # <- copepod is gone, unclassified as well, replaced with entomobryomorpha
        }
    ]

    sce_check_consistency("classify all no change after revert")

    # Reset to predicted on validated objects, i.e. all of them
    url = OBJECT_SET_RESET_PREDICTED_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()

    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 9,
        "nb_unclassified": 0,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [entomobryomorpha_id],  # No change as it's "forced to Predicted"
    }

    assert get_predictions_stats(obj_ids) == {
        "n_trainings": 2,  # new pseudo-training
        "n_objects_in_predictions": 8,  # all of them
        "n_predictions": 8,  # 8 new (single score, single prediction line)
        "n_predictions_h": 3,  # the one with 3 scores remains in archive
        "n_discarded": 0,
    }

    sce_check_consistency("Reset to predicted on validated objects after revert")

    # What would a revert of the force do?
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    dry_run_output = rsp.json()
    for an_entry in dry_run_output["last_entries"]:
        assert (
            an_entry["histo_classif_date"] is not None
        )  # e.g. 2024-09-21T09:07:56.930458
        an_entry["histo_classif_date"] = "now"
        an_entry["objid"] = 9999999
    assert dry_run_output == {
        "classif_info": {"25835": ["Entomobryomorpha", "Collembola"]},
        "last_entries": [
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
            {
                "classif_id": 25835,
                "histo_classif_date": "now",
                "histo_classif_id": 25835,
                "histo_classif_qual": "V",
                "histo_classif_who": 1,
                "histo_classif_score": None,
                "histo_classif_type": "M",
                "objid": 9999999,
            },
        ],
    }

    # Revert after reset to predicted
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=False, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()

    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 0,
        "nb_unclassified": 0,
        "nb_validated": 9,
        "projid": prj_id,
        "used_taxa": [entomobryomorpha_id],
    }

    sce_check_consistency("revert of force after revert")

    # Delete some object via API, leave the one which was predicted twice (#1)
    rsp = fastapi.delete(OBJECT_SET_DELETE_URL, headers=ADMIN_AUTH, json=obj_ids[2:6])
    assert rsp.status_code == status.HTTP_200_OK
    # They should disappear from some predictions
    assert get_predictions_stats(obj_ids) == {
        "n_trainings": 1,  # left non-empty trainings
        "n_objects_in_predictions": 1,  # the one left
        "n_predictions": 0,  # left predictions
        "n_predictions_h": 3,  # left predictions
        "n_discarded": 0,
    }

    # Ensure they are gone
    rsp = fastapi.post(OBJECT_SET_PARENTS_URL, headers=ADMIN_AUTH, json=obj_ids)
    assert rsp.status_code == status.HTTP_200_OK
    resp = rsp.json()
    assert len(resp["acquisition_ids"]) == 5
    for prj in resp["project_ids"]:
        assert prj == prj_id
    assert resp["total_ids"] == 5

    # Try user stats on the project
    url = PROJECT_SET_USER_STATS.format(prj_ids=str(prj_id))
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    stats = rsp.json()
    ref_stats = [
        {
            "projid": prj_id,
            "annotators": [{"id": 1, "name": "Application Administrator"}],
            "activities": [
                {"id": 1, "nb_actions": 8, "last_annot": "2022-05-12T14:21:15"}
            ],
        }
    ]
    # Fix the date on both sides
    ref_stats[0]["activities"][0]["last_annot"] = "FIXED DATE"
    stats[0]["activities"][0]["last_annot"] = "FIXED DATE"
    assert stats == ref_stats

    sce_check_consistency("inside")


def dry_run_revert(fastapi, prj_id):
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    return stats


def test_reset_fresh_import(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import

    prj_id = test_import(
        database, caplog, "Test reset to pred", path=str(VARIOUS_STATES_DIR)
    )

    # Reset all to predicted
    url = OBJECT_SET_RESET_PREDICTED_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK

    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 8,
        "nb_unclassified": 1,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [-1, 45072, 78418, 84963, 85011, 85012, 85078],
    }


def test_revert_to_predicted(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    prj_id = create_project(CREATOR_USER_ID, "Test Revert To Predicted")

    import_various(fastapi, prj_id)
    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 9

    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 1,
        "nb_predicted": 3,
        "nb_unclassified": 1,
        "nb_validated": 4,
        "projid": prj_id,
        "used_taxa": [-1, 45072, 78418, 84963, 85011, 85012, 85078],
    }

    classify_all(fastapi, obj_ids, copepod_id, CREATOR_AUTH)

    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=False, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    min_obj_id = min(obj_ids)
    for an_entry in stats["last_entries"]:
        if an_entry["histo_classif_date"] is not None:
            an_entry["histo_classif_date"] = "JUSTNOW"
        an_entry["objid"] -= min_obj_id - 1
    assert stats == {
        "classif_info": {},
        "last_entries": [
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 85012,
                "histo_classif_qual": "P",
                "histo_classif_type": "A",
                "histo_classif_who": None,
                "objid": 1,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 78418,
                "histo_classif_qual": "V",
                "histo_classif_type": "M",
                "histo_classif_who": 1,
                "objid": 2,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 45072,
                "histo_classif_qual": "V",
                "histo_classif_type": "M",
                "histo_classif_who": 1,
                "objid": 3,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 85011,
                "histo_classif_qual": "P",
                "histo_classif_type": "A",
                "histo_classif_who": None,
                "objid": 4,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 78418,
                "histo_classif_qual": "D",
                "histo_classif_type": "M",
                "histo_classif_who": 1,
                "objid": 5,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 84963,
                "histo_classif_qual": "P",
                "histo_classif_type": "A",
                "histo_classif_who": None,
                "objid": 6,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 84963,
                "histo_classif_qual": "V",
                "histo_classif_type": "M",
                "histo_classif_who": 1,
                "objid": 7,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": "JUSTNOW",
                "histo_classif_id": 85078,
                "histo_classif_qual": "V",
                "histo_classif_type": "M",
                "histo_classif_who": 1,
                "objid": 8,
            },
            {
                "classif_id": copepod_id,
                "histo_classif_date": None,
                "histo_classif_id": None,
                "histo_classif_qual": None,
                "histo_classif_type": "n",
                "histo_classif_who": None,
                "objid": 9,
            },
        ],
    }
