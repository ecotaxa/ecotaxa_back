# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

from starlette import status

from tests.credentials import CREATOR_AUTH

OBJECT_SET_QUERY_URL = "/object_set/{project_id}/query"  # ?order_field={order}&window_start={start}&window_size={size}"


# TODO: Dup/extend of the same in test_classification.py
def _prj_query(
    fastapi, auth, prj_id, order=None, start=None, size=None, fields=None, **kwargs
):
    """Query using the filters in kwargs"""
    params = []
    if fields:
        params.append("fields=%s" % fields)
    if order:
        params.append("order_field=%s" % order)
    if start:
        params.append("window_start=%s" % start)
    if size:
        params.append("window_size=%s" % size)
    if params:
        params.insert(0, "?")
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id) + "&".join(params)
    rsp = fastapi.post(url, headers=auth, json=kwargs)
    assert rsp.status_code == status.HTTP_200_OK
    obj_ids = rsp.json()["object_ids"]
    details = rsp.json()["details"]
    return obj_ids if fields is None else (obj_ids, details)


def test_queries(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping

    prj_id = test_import(database, caplog, "Queries test project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(database, caplog, "Queries test project")

    ref = [6, 7, 8, 11, 12, 13, 1, 2, 3, 4, 5]
    all = _prj_query(fastapi, CREATOR_AUTH, prj_id, order="obj.depth_min")
    # we must offset expected by first actual objID as they vary, run to run
    min_objid = min(all)
    ref = [r + min_objid - 1 for r in ref]
    assert all == ref

    all = _prj_query(fastapi, CREATOR_AUTH, prj_id, order="-obj.depth_min")
    ref_v = ref[:]
    ref_v.reverse()
    assert all == ref_v

    by_taxo_rev = _prj_query(fastapi, CREATOR_AUTH, prj_id, order="-txo.name")
    by_taxo = _prj_query(fastapi, CREATOR_AUTH, prj_id, order="txo.name")
    assert by_taxo == list(reversed(by_taxo_rev))

    by_free_col = _prj_query(fastapi, CREATOR_AUTH, prj_id, order="fre.area")
    by_free_col_rev = _prj_query(fastapi, CREATOR_AUTH, prj_id, order="-fre.area")
    assert by_free_col == list(reversed(by_free_col_rev))

    limit_4 = _prj_query(fastapi, CREATOR_AUTH, prj_id, size=4, order="obj.objid")
    assert len(limit_4) == 4

    limit_4_start_4 = _prj_query(
        fastapi, CREATOR_AUTH, prj_id, start=4, size=4, order="obj.objid"
    )
    assert len(limit_4_start_4) == 4

    assert set(limit_4).isdisjoint(set(limit_4_start_4))

    # What we get from UI, std page
    objs, details = _prj_query(
        fastapi, CREATOR_AUTH, prj_id, fields="img.file_name,img.thumb_file_name"
    )
    there_was_a_mini = False
    for a_det_list in details:
        file_name, thumb_file_name = a_det_list
        assert file_name.endswith(".jpg") or file_name.endswith(".png")
        if thumb_file_name:
            there_was_a_mini = True
            assert file_name[:9] == thumb_file_name[:9]
    assert there_was_a_mini
