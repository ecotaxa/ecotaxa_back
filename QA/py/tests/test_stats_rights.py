# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Rights on stats-like entry points, which used to check nothing on their projects:
# project collections, project set taxo/column stats, reclassification history/stats.
from starlette import status

from tests.credentials import (
    ADMIN_AUTH,
    ORDINARY_USER2_USER_ID,
    USER2_AUTH,
    USER_AUTH,
)
from tests.test_collections_recast import _add_privilege, _remove_privilege
from tests.test_import import do_test_import

TAXO_STATS_URL = "/project_set/taxo_stats"
COLUMN_STATS_URL = "/project_set/column_stats"
PROJECT_COLLECTIONS_URL = "/projects/{project_id}/collections"
RECLASSIF_HISTORY_URL = "/taxa/reclassification_history/{project_id}"
RECLASSIF_STATS_URL = "/taxa/reclassification_stats"


def _set_access(fastapi, prj_id, access):
    rsp = fastapi.patch(
        f"/projects/{prj_id}", headers=ADMIN_AUTH, json={"access": access}
    )
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    rsp = fastapi.get(f"/projects/{prj_id}", headers=ADMIN_AUTH)
    assert rsp.json()["access"] == access


def test_stats_rights_on_private_project(fastapi):
    # A PRIVATE project with a View member (USER2), and a PUBLIC one.
    # USER is active and has no privilege on either
    prj_id = do_test_import(fastapi, "Stats rights private project")
    _set_access(fastapi, prj_id, "0")
    pub_prj_id = do_test_import(fastapi, "Stats rights public project")
    _add_privilege(prj_id, ORDINARY_USER2_USER_ID, "View")
    # Other tests expect USER2 to have no privilege
    try:
        single = [
            PROJECT_COLLECTIONS_URL.format(project_id=prj_id),
            RECLASSIF_HISTORY_URL.format(project_id=prj_id),
        ]
        taxo_stats = (TAXO_STATS_URL, {"ids": str(prj_id)})
        column_stats = (
            COLUMN_STATS_URL,
            {"ids": str(prj_id), "names": "obj.depth_min"},
        )
        for url in single:
            # Anonymous and no privilege: refused
            assert fastapi.get(url).status_code == status.HTTP_403_FORBIDDEN, url
            rsp = fastapi.get(url, headers=USER_AUTH)
            assert rsp.status_code == status.HTTP_403_FORBIDDEN, url
            # View member: allowed
            rsp = fastapi.get(url, headers=USER2_AUTH)
            assert rsp.status_code == status.HTTP_200_OK, url
        for url, params in (taxo_stats, column_stats):
            rsp = fastapi.get(url, params=params)
            assert rsp.status_code == status.HTTP_403_FORBIDDEN, url
            rsp = fastapi.get(url, headers=USER_AUTH, params=params)
            assert rsp.status_code == status.HTTP_403_FORBIDDEN, url
            rsp = fastapi.get(url, headers=USER2_AUTH, params=params)
            assert rsp.status_code == status.HTTP_200_OK, url
            # A set is refused as a whole if one project is not readable
            mixed = dict(params, ids=f"{pub_prj_id} {prj_id}")
            rsp = fastapi.get(url, headers=USER_AUTH, params=mixed)
            assert rsp.status_code == status.HTTP_403_FORBIDDEN, url
            rsp = fastapi.get(url, headers=USER2_AUTH, params=mixed)
            assert rsp.status_code == status.HTTP_200_OK, url
    finally:
        _remove_privilege(prj_id, ORDINARY_USER2_USER_ID)


def test_reclassif_stats_needs_user(fastapi):
    params = {"taxa_ids": "84963"}
    rsp = fastapi.get(RECLASSIF_STATS_URL, params=params)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    rsp = fastapi.get(RECLASSIF_STATS_URL, headers=USER_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK


def test_stats_rights_anonymous_on_open_project(fastapi):
    # Anonymous visitors (e.g. the front's explore page) still see OPEN projects stats
    open_prj_id = do_test_import(fastapi, "Stats rights open project")
    _set_access(fastapi, open_prj_id, "2")
    priv_prj_id = do_test_import(fastapi, "Stats rights other private project")
    _set_access(fastapi, priv_prj_id, "0")
    for url in (
        PROJECT_COLLECTIONS_URL.format(project_id=open_prj_id),
        RECLASSIF_HISTORY_URL.format(project_id=open_prj_id),
    ):
        assert fastapi.get(url).status_code == status.HTTP_200_OK, url
    params = {"ids": str(open_prj_id), "taxa_ids": "all"}
    rsp = fastapi.get(TAXO_STATS_URL, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    assert {row["projid"] for row in rsp.json()} == {open_prj_id}
    # Not when the set also holds a PRIVATE project
    params["ids"] = f"{open_prj_id}+{priv_prj_id}"
    rsp = fastapi.get(TAXO_STATS_URL, params=params)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
