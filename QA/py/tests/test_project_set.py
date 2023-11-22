# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
from API_operations.helpers.Service import Service
from BO.ProjectSet import FeatureConsistentProjectSet, LimitedInCategoriesProjectSet
from starlette import status

from test_export_emodnet import create_test_collection
from tests.credentials import ADMIN_AUTH
from tests.test_classification import OBJECT_SET_CLASSIFY_URL
from tests.test_objectset_query import _prj_query
from tests.test_collections import COLLECTION_QUERY_URL


def test_project_set(database, fastapi, caplog):
    # Functions used during prediction
    # Reuse the collection functions, as there are 2 projects there
    coll_id, coll_title, prj_id = create_test_collection(
        database, fastapi, caplog, "prj_set_tst"
    )
    url = COLLECTION_QUERY_URL.format(collection_id=coll_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    ids = rsp.json()["project_ids"]
    assert len(ids) == 2
    # Prediction runs on validated objects
    for prj_id in ids:
        # Validate all
        obj_ids = _prj_query(fastapi, ADMIN_AUTH, prj_id)
        url = OBJECT_SET_CLASSIFY_URL
        classifications = [-1 for _obj in obj_ids]  # Keep current
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
    # Build dataset
    features = ["fre.major", "fre.minor", "fre.feret", "fre.esd"]
    with Service() as sce:
        prj_set = FeatureConsistentProjectSet(
            session=sce.ro_session, prj_ids=ids, column_names=features
        )
        stats = prj_set.read_columns_stats()
        assert stats.counts == (21, 21, 21, 2)
        median = prj_set.read_median_values()
        assert median == {
            "fre.esd": 1.935,
            "fre.feret": 53.0999984741211,
            "fre.major": 48.9000015258789,
            "fre.minor": 25.3999996185303,
        }
        np_learning_set, obj_ids, classif_ids = prj_set.np_read_all()
        # Unpredictable ids
        assert len(obj_ids) == len(classif_ids) == 21
    with Service() as sce:
        prj_set2 = LimitedInCategoriesProjectSet(
            session=sce.ro_session,
            prj_ids=ids,
            column_names=features,
            random_limit=4,  # More objects present than random, so output is predictable
            categories=[92731],
        )
        stats = prj_set2.read_columns_stats()
        assert stats.counts == (2, 2, 2, 2)
        median = prj_set2.read_median_values()
        assert median == {
            "fre.esd": 1.935,
            "fre.feret": 29.100000381469748,
            "fre.major": 27.5,
            "fre.minor": 22.05000019073485,
        }
        np_learning_set, obj_ids, classif_ids = prj_set2.np_read_all()
        assert len(obj_ids) == len(classif_ids) == 2
