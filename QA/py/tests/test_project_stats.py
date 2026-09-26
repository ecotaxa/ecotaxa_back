# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from starlette import status

from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.test_project_set import setup_test_projects_for_column_stats

PROJECT_SET_COLUMN_STATS_URL = "/project_set/column_stats"


def test_project_set_column_stats(fastapi):
    ids = setup_test_projects_for_column_stats(fastapi, "prj_col_stats")
    prj_ids_str = ",".join(str(i) for i in ids)
    prj_ids_plus_str = "+".join(str(i) for i in ids)

    features = [
        "obj.depth_min",
        "obj.depth_max",
        "fre.major",
        "fre.minor",
        "fre.feret",
        "fre.esd",
    ]
    names_str = ",".join(features)

    # 1. Unauthenticated request should fail
    rsp = fastapi.get(
        f"{PROJECT_SET_COLUMN_STATS_URL}?ids={prj_ids_str}&names={names_str}"
    )
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    def _check_stats(s_url, headers, expected_total, expected_counts):
        res = fastapi.get(s_url, headers=headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["proj_ids"] == ids
        assert data["total"] == expected_total
        assert data["columns"] == features
        assert data["counts"] == expected_counts
        assert len(data["variances"]) == len(features)
        assert all(v is not None for v in data["variances"])

    # 2 & 5. Authenticated requests for all validated objects (full set)
    for url, auth in [
        (
            f"{PROJECT_SET_COLUMN_STATS_URL}?ids={prj_ids_str}&names={names_str}",
            ADMIN_AUTH,
        ),
        (
            f"{PROJECT_SET_COLUMN_STATS_URL}?ids={prj_ids_plus_str}&names={names_str}",
            USER_AUTH,
        ),
    ]:
        _check_stats(
            url, auth, expected_total=21, expected_counts=[21, 21, 21, 21, 21, 2]
        )

    # 3 & 4. Filtered by category (with / without limit)
    for url in [
        f"{PROJECT_SET_COLUMN_STATS_URL}?ids={prj_ids_str}&names={names_str}&categories=92731",
        f"{PROJECT_SET_COLUMN_STATS_URL}?ids={prj_ids_str}&names={names_str}&categories=92731&limit=4",
    ]:
        _check_stats(
            url, ADMIN_AUTH, expected_total=2, expected_counts=[2, 2, 2, 2, 2, 2]
        )
