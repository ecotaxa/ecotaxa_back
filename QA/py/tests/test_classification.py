# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
import pytest

from typing import List

import pytest
from API_models.filters import ProjectFiltersDict
from API_operations.helpers.Service import Service
from DB.Object import ObjectHeader
from DB.Prediction import Prediction
from DB.helpers import Result
from DB.helpers.Core import select
from DB.helpers.ORM import any_, and_
from starlette import status

from tests.credentials import CREATOR_AUTH, ORDINARY_USER2_USER_ID, ADMIN_AUTH
from tests.test_import import VARIOUS_STATES_DIR
from tests.test_objectset_query import OBJECT_SET_QUERY_URL
from tests.test_prj_admin import PROJECT_CLASSIF_STATS_URL
from tests.test_subentities import OBJECT_HISTORY_QUERY_URL
from tests.test_taxa_query import TAXA_SET_QUERY_URL


def query_all_objects(fastapi, auth, prj_id, **kwargs) -> List[int]:
    """Query using the filters in kwargs,return the full list of object IDs"""
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=auth, json=kwargs)
    obj_ids = rsp.json()["object_ids"]
    return obj_ids


OBJECT_SET_REVERT_URL = (
    "/object_set/{project_id}/revert_to_history?dry_run={dry_run}{tgt_usr}"
)
OBJECT_SET_RESET_PREDICTED_URL = "/object_set/{project_id}/reset_to_predicted"
OBJECT_SET_CLASSIFY_URL = "/object_set/classify"
OBJECT_SET_CLASSIFY_AUTO_URL = "/object_set/classify_auto"
OBJECT_SET_CLASSIFY_AUTO_URL2 = "/object_set/classify_auto_multiple"
OBJECT_SET_DELETE_URL = "/object_set/"
OBJECT_SET_SUMMARY_URL = "/object_set/{project_id}/summary?only_total=False"
OBJECT_SET_PARENTS_URL = "/object_set/parents"
OBJECT_QUERY_URL = "/object/{object_id}"

PROJECT_SET_USER_STATS = "/project_set/user_stats?ids={prj_ids}"

copepod_id = 25828
entomobryomorpha_id = 25835
crustacea = 12846


def classif_history(fastapi, object_id):
    url = OBJECT_HISTORY_QUERY_URL.format(object_id=object_id)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    return response.json()


def get_stats(fastapi, prj_id):
    stats_url = PROJECT_CLASSIF_STATS_URL.format(prj_ids="%s" % prj_id)
    stats_rsp = fastapi.get(stats_url, headers=ADMIN_AUTH)
    assert stats_rsp.status_code == status.HTTP_200_OK
    return stats_rsp.json()[0]


def get_predictions_stats(obj_ids):
    with Service() as sce:
        qry = select(
            Prediction.object_id, Prediction.training_id
        )  # TODO: makes sense to update this
        qry = qry.where(Prediction.object_id == any_(obj_ids))
        res: Result = sce.session.execute(qry)
        pred_stats = {
            "n_predicted_objects": 0,
            "n_predictions": 0,
            "n_discarded": 0,
            "n_trainings": 0,
        }
        pred_objects = list()
        trainings = set()
        for rec in res.fetchall():
            if rec["object_id"] not in pred_objects:
                pred_objects.append(rec["object_id"])
                pred_stats["n_predicted_objects"] += 1
            pred_stats["n_predictions"] += 1
            trainings.add(rec["training_id"])
        pred_stats["n_trainings"] = len(trainings)
        # if rec["discarded"]:
        #     pred_stats["n_discarded"] += 1
    return pred_stats


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
def test_classif(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import

    prj_id = test_import(
        database, caplog, "Test Classify/Validate", path=str(VARIOUS_STATES_DIR)
    )

    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 8

    # See if the taxa we are going to use are OK
    rsp = fastapi.get(
        TAXA_SET_QUERY_URL.format(taxa_ids="%d+%d" % (copepod_id, entomobryomorpha_id))
    )
    # Note: There is no real lineage in test DB
    assert rsp.json() == [
        {
            "children": [84964],
            "display_name": "Copepoda",
            "id": 25828,
            "id_lineage": [25828, 16621, 12846, 11517, 2367, 382, 8, 2, 1],
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

    def get_object_set_stats():
        stats_url = OBJECT_SET_SUMMARY_URL.format(project_id=prj_id)
        filters = ProjectFiltersDict()
        stats_rsp = fastapi.post(stats_url, headers=ADMIN_AUTH, json=filters)
        assert stats_rsp.status_code == status.HTTP_200_OK
        return stats_rsp.json()

    # We have a like-in-real-life mix of states
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 1,
        "nb_predicted": 3,
        "nb_unclassified": 0,
        "nb_validated": 4,
        "projid": prj_id,
        "used_taxa": [45072, 78418, 84963, 85011, 85012, 85078],
    }

    assert get_predictions_stats(obj_ids) == {
        "n_predicted_objects": 3,
        "n_predictions": 3,
        "n_trainings": 1,  # import creates a pseudo-prediction
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
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    assert len(stats["classif_info"]) == 6
    assert len(stats["last_entries"]) == 8
    # Working revert, erase all from import
    url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=False, tgt_usr="")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK
    stats = rsp.json()
    # assert stats == {'classif_info': {}, 'last_entries': []}

    # Same stats
    assert get_stats(fastapi, prj_id) == {
        "nb_dubious": 0,
        "nb_predicted": 0,
        "nb_unclassified": 8,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [-1],
    }

    obj_stats = get_object_set_stats()
    assert obj_stats == {
        "dubious_objects": 0,
        "predicted_objects": 0,
        "total_objects": 8,
        "validated_objects": 0,
    }

    # # Reset all to predicted. This does nothing as no objet is in target state (dubious or validated)
    # url = OBJECT_SET_RESET_PREDICTED_URL.format(project_id=prj_id)
    # rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    # assert rsp.status_code == status.HTTP_200_OK
    #
    # # Incorrect ML results
    # classify_auto_incorrect(fastapi, obj_ids[:4])
    #
    # # Super ML result, 4 first objects are crustacea with same scores
    # classify_auto_mult_all(
    #     fastapi,
    #     obj_ids[:4],
    #     [crustacea, copepod_id, entomobryomorpha_id],
    #     [[0.52, 0.2, 0.08]] * 4,
    # )
    #
    # assert get_stats(fastapi, prj_id) == {
    #     "nb_dubious": 0,
    #     "nb_predicted": 4,
    #     "nb_unclassified": 4,
    #     "nb_validated": 0,
    #     "projid": prj_id,
    #     "used_taxa": [-1, crustacea],
    # }
    #
    # assert get_predictions_stats(obj_ids) == {
    #     "n_predicted_objects": 4,
    #     "n_predictions": 12,
    #     "n_discarded": 0,
    # }
    #
    # # New ML results with a different score for the second object
    # classify_auto_mult_all(
    #     fastapi,
    #     [obj_ids[1]],
    #     [crustacea, copepod_id, entomobryomorpha_id],
    #     [[0.8, 0.1, 0.05]],
    # )
    # url = OBJECT_QUERY_URL.format(object_id=obj_ids[1])
    # rsp = fastapi.get(url, headers=ADMIN_AUTH)
    # assert rsp.status_code == status.HTTP_200_OK
    # # assert rsp.json()["classif_auto_score"] == 0.8
    #
    # assert get_stats(fastapi, prj_id) == {
    #     "nb_dubious": 0,
    #     "nb_predicted": 4,
    #     "nb_unclassified": 4,
    #     "nb_validated": 0,
    #     "projid": prj_id,
    #     "used_taxa": [-1, crustacea],
    # }
    #
    # assert get_predictions_stats(obj_ids) == {
    #     "n_predicted_objects": 4,
    #     "n_predictions": 15,  # +3 predictions, first training is kept for eventual revert
    #     "n_discarded": 0,
    # }
    #
    # with Service() as sce:
    #     # Get _last_ training stored results for second object
    #     qry = select(Prediction.classif_id, Prediction.score).join(ObjectHeader)
    #     qry = qry.where(
    #         and_(
    #             Prediction.object_id == ObjectHeader.objid,
    #             Prediction.training_id == ObjectHeader.training_id,
    #             ObjectHeader.objid == obj_ids[1],
    #         )
    #     )
    #     res: Result = sce.session.execute(qry)
    #     assert res.fetchall() == [
    #         (crustacea, 0.8),
    #         (copepod_id, 0.1),
    #         (entomobryomorpha_id, 0.05),
    #     ]
    #
    # # Admin (me!) thinks that all is a copepod :)
    # classify_all(fastapi, obj_ids, copepod_id)
    #
    # # Same stats
    # assert get_stats(fastapi, prj_id) == {
    #     "nb_dubious": 0,
    #     "nb_predicted": 0,
    #     "nb_unclassified": 0,
    #     "nb_validated": 8,
    #     "projid": prj_id,
    #     "used_taxa": [copepod_id],
    # }  # No more Unclassified and Copepod is in +
    #
    # # No history yet as the object was just created
    # classif = classif_history(fastapi, obj_ids[0])
    # assert len(classif) == 1
    # assert classif[0]["classif_date"] is not None  # e.g. 2021-09-12T09:28:03.278626
    # classif[0]["classif_date"] = "now"
    # assert classif == [
    #     {
    #         "objid": obj_ids[0],
    #         "classif_id": crustacea,
    #         "classif_date": "now",
    #         "classif_who": None,
    #         "classif_type": "A",
    #         "classif_qual": "P",
    #         "classif_score": 0.52,  # Highest score
    #         "user_name": None,
    #         "taxon_name": "Crustacea",
    #     }
    # ]
    #
    # # Revert on validated objects
    # url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=False, tgt_usr="")
    # rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    # assert rsp.status_code == status.HTTP_200_OK
    # stats = rsp.json()
    #
    # assert get_stats(fastapi, prj_id) == {
    #     "nb_dubious": 0,
    #     "nb_predicted": 4,
    #     "nb_unclassified": 4,
    #     "nb_validated": 0,
    #     "projid": prj_id,
    #     "used_taxa": [-1, crustacea],
    # }
    #
    # # Second revert, should not change since the last record in history is the same
    # rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    # assert rsp.status_code == status.HTTP_200_OK
    # stats = rsp.json()
    #
    # assert get_stats(fastapi, prj_id) == {
    #     "nb_dubious": 0,
    #     "nb_predicted": 4,
    #     "nb_unclassified": 4,
    #     "nb_validated": 0,
    #     "projid": prj_id,
    #     "used_taxa": [-1, crustacea],
    # }
    #
    # # Apply validation again after revert
    # classify_all(fastapi, obj_ids, copepod_id)
    #
    # # Not a copepod :(
    # classify_all(fastapi, obj_ids, entomobryomorpha_id)
    #
    # def classify_all_no_change(classif_id):
    #     url = OBJECT_SET_CLASSIFY_URL
    #     classifications = [-1 for _obj in obj_ids]
    #     rsp = fastapi.post(
    #         url,
    #         headers=ADMIN_AUTH,
    #         json={
    #             "target_ids": obj_ids,
    #             "classifications": classifications,
    #             "wanted_qualification": "V",
    #         },
    #     )
    #     assert rsp.status_code == status.HTTP_200_OK
    #
    # classify_all_no_change(entomobryomorpha_id)
    #
    # classif2 = classif_history(fastapi, obj_ids[0])
    # assert classif2 is not None
    # # Date is not predictable
    # classif2[0]["classif_date"] = "hopefully just now"
    # classif2[1]["classif_date"] = "a bit before"
    # assert classif2 == [
    #     {
    #         "classif_date": "hopefully just now",
    #         "classif_id": copepod_id,
    #         "classif_qual": "V",
    #         "classif_score": 0.2,
    #         "classif_type": "M",
    #         "classif_who": 1,
    #         "objid": obj_ids[0],
    #         "taxon_name": "Copepoda",
    #         "user_name": "Application Administrator",
    #     },
    #     {
    #         "classif_date": "a bit before",
    #         "classif_id": crustacea,
    #         "classif_qual": "P",
    #         "classif_score": 0.52,
    #         "classif_type": "A",
    #         "classif_who": None,
    #         "objid": obj_ids[0],
    #         "taxon_name": "Crustacea",
    #         "user_name": None,
    #     },
    # ]
    #
    # # There should be 0 predicted
    # obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id, statusfilter="P")
    # assert len(obj_ids) == 0
    # # There should be 8 validated
    # obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id, statusfilter="V")
    # assert len(obj_ids) == 8
    #
    # url = PROJECT_CLASSIF_STATS_URL.format(prj_ids="%s" % prj_id)
    # rsp = fastapi.get(url, headers=ADMIN_AUTH)
    # assert rsp.status_code == status.HTTP_200_OK
    # assert rsp.json() == [
    #     {
    #         "nb_dubious": 0,
    #         "nb_predicted": 0,
    #         "nb_unclassified": 0,
    #         "nb_validated": 8,
    #         "projid": prj_id,
    #         "used_taxa": [
    #             entomobryomorpha_id
    #         ],  # <- copepod is gone, unclassified as well, replaced with entomobryomorpha
    #     }
    # ]  # <- copepod is gone, unclassified as well, replaced with entomobryomorpha
    #
    # # Reset to predicted on validated objects
    # url = OBJECT_SET_RESET_PREDICTED_URL.format(project_id=prj_id)
    # rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    # assert rsp.status_code == status.HTTP_200_OK
    # stats = rsp.json()
    #
    # assert get_stats(fastapi, prj_id) == {
    #     "nb_dubious": 0,
    #     "nb_predicted": 8,
    #     "nb_unclassified": 0,
    #     "nb_validated": 0,
    #     "projid": prj_id,
    #     "used_taxa": [entomobryomorpha_id],  # No change as it's "forced to Predicted"
    # }
    #
    # # What would a revert of the force do?
    # url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=True, tgt_usr="")
    # rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    # assert rsp.status_code == status.HTTP_200_OK
    # dry_run_output = rsp.json()  # TODO: assert
    #
    # # Revert after reset to predicted
    # url = OBJECT_SET_REVERT_URL.format(project_id=prj_id, dry_run=False, tgt_usr="")
    # rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})
    # assert rsp.status_code == status.HTTP_200_OK
    # stats = rsp.json()
    #
    # assert get_stats(fastapi, prj_id) == {
    #     "nb_dubious": 0,
    #     "nb_predicted": 0,
    #     "nb_unclassified": 0,
    #     "nb_validated": 8,
    #     "projid": prj_id,
    #     "used_taxa": [entomobryomorpha_id],
    # }
    #
    # # Delete some object via API, why not?
    # rsp = fastapi.delete(OBJECT_SET_DELETE_URL, headers=ADMIN_AUTH, json=obj_ids[:4])
    # assert rsp.status_code == status.HTTP_200_OK
    #
    # # Ensure they are gone
    # rsp = fastapi.post(OBJECT_SET_PARENTS_URL, headers=ADMIN_AUTH, json=obj_ids)
    # assert rsp.status_code == status.HTTP_200_OK
    # resp = rsp.json()
    # assert len(resp["acquisition_ids"]) == 4
    # for prj in resp["project_ids"]:
    #     assert prj == prj_id
    # assert resp["total_ids"] == 4
    #
    # # Try user stats on the project
    # url = PROJECT_SET_USER_STATS.format(prj_ids=str(prj_id))
    # rsp = fastapi.get(url, headers=ADMIN_AUTH)
    # stats = rsp.json()
    # # The ref stats were obtained with a run in may 2022
    # ref_stats = [
    #     {
    #         "projid": prj_id,
    #         "annotators": [{"id": 1, "name": "Application Administrator"}],
    #         "activities": [
    #             {"id": 1, "nb_actions": 12, "last_annot": "2022-05-12T14:21:15"}
    #         ],
    #     }
    # ]
    # # Fix the date on both sides
    # ref_stats[0]["activities"][0]["last_annot"] = "FIXED DATE"
    # stats[0]["activities"][0]["last_annot"] = "FIXED DATE"
    # assert stats == ref_stats


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
        "nb_unclassified": 0,
        "nb_validated": 0,
        "projid": prj_id,
        "used_taxa": [45072, 78418, 84963, 85011, 85012, 85078],
    }
