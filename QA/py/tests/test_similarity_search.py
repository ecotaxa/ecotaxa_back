import logging

import numpy as np
import pandas as pd
from API_operations.CRUD.ObjectParents import SamplesService
from BO.Prediction import DeepFeatures
from starlette import status

from tests.credentials import ADMIN_AUTH
from tests.test_classification import classify_all
from tests.test_objectset_query import _prj_query, OBJECT_SET_QUERY_URL

copepod_id = 25828
entomobryomorpha_id = 25835
crustacea = 12846


def similarity_scores(distances_to_target):
    return [round(1 - d / max(distances_to_target), 4) for d in distances_to_target]


def test_similarity_search(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import

    prj_id = test_import(database, caplog, "Test Similarity Search")

    obj_ids = _prj_query(fastapi, ADMIN_AUTH, prj_id)
    assert len(obj_ids) == 8

    # Prepare dummy features
    features = list()
    for i, oi in enumerate(obj_ids):
        features.append([(i + 1) * 0.1] * 50)
    features_df = pd.DataFrame(features, index=obj_ids)

    target_id = obj_ids[0]
    distances_to_target = [
        np.linalg.norm(features_df.loc[target_id] - features_df.loc[oi])
        for oi in obj_ids
    ]

    # Test similarity search without features
    url = f"/object_set/{prj_id}/similarity_search/{target_id}"
    req = {
        "project_id": prj_id,
        "target_id": target_id,
    }
    filters = {}
    req_and_filters = {"filters": filters, "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)

    assert rsp.status_code == status.HTTP_200_OK
    assert (
        rsp.json()["message"]
        == "Project has no feature extractor, choose one in project settings."
    )
    assert rsp.json()["neighbor_ids"] == []
    assert rsp.json()["sim_scores"] == []

    # Insert dummy features
    with SamplesService() as sce:
        n_inserts = DeepFeatures.save(sce.session, features_df)
        assert n_inserts == 8
        sce.session.commit()

    # Test similarity search with a limit
    url += "?size=3"
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)

    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["message"] == "Success"
    assert len(rsp.json()["neighbor_ids"]) == 3

    # Limit of 1 should return only the seed
    url = url.replace("size=3", "size=1")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)

    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["message"] == "Success"
    assert rsp.json()["neighbor_ids"] == [target_id]
    assert rsp.json()["sim_scores"] == [1]

    # Limit of 0 should return nothing
    url = url.replace("size=1", "size=0")
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)

    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["message"] == "Success"
    assert rsp.json()["neighbor_ids"] == []
    assert rsp.json()["sim_scores"] == []

    # Test object search with similarity
    url = (
        OBJECT_SET_QUERY_URL.format(project_id=prj_id) + f"?order_field=ss-I{target_id}"
    )
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})

    assert rsp.status_code == status.HTTP_200_OK
    rsp_obj_ids = rsp.json()["object_ids"]
    assert rsp_obj_ids == obj_ids
    # assert rsp.json()["sim_scores"] == similarity_scores(distances_to_target)

    # Set different taxo ids
    classify_all(fastapi, obj_ids[0:3], copepod_id)
    classify_all(fastapi, obj_ids[3:5], entomobryomorpha_id)
    classify_all(fastapi, obj_ids[5:8], crustacea)
    taxo_ids_to_filter = [copepod_id, entomobryomorpha_id]

    # Test object search with similarity and filters on taxo
    filters["taxo"] = ",".join([str(taxo_id) for taxo_id in taxo_ids_to_filter])
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=filters)

    assert rsp.status_code == status.HTTP_200_OK
    json_rsp = rsp.json()
    rsp_obj_ids = json_rsp["object_ids"]
    assert rsp_obj_ids == obj_ids[0:5]
    # TODO: We have a distance not a similarity
    # scores = [e[0] for e in json_rsp["details"]]
    # assert scores == similarity_scores(distances_to_target[0:5])

    # Test object search with inverse similarity
    url = (
        OBJECT_SET_QUERY_URL.format(project_id=prj_id)
        + f"?order_field=-ss-I{target_id}"
    )
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={})

    assert rsp.status_code == status.HTTP_200_OK
    rsp_obj_ids = rsp.json()["object_ids"]
    assert rsp_obj_ids == list(reversed(obj_ids))
