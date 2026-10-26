# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

from starlette import status

from API_models.filters import ObjectSetQueryFilters
from tests.credentials import CREATOR_AUTH
from tests.test_import import do_test_import, do_import_a_bit_more_skipping

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


def test_queries(fastapi):

    # Admin imports the project

    prj_id = do_test_import(fastapi, "Queries test project")
    # Add a sample spanning 2 days
    do_import_a_bit_more_skipping(fastapi, "Queries test project")

    ref = [6, 7, 8, 9, 10, 11, 1, 2, 3, 4, 5]  # No gap as no DB sequence anymore
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


def test_all_fields(fastapi):
    # Ensure that all API-documented fields work

    # Admin imports the project
    prj_id = do_test_import(fastapi, "Full Queries test project")
    # Add a sample spanning 2 days
    do_import_a_bit_more_skipping(fastapi, "Full Queries test project")

    # Copy/paste from redoc API
    # prj_fields = "title, status" Not in API
    sam_fields = "orig_id, latitude"
    acq_fields = "orig_id, instrument, acquisid"
    # prc_fields = "orig_id, processid" Not in API
    obj_fields = "imgcount, classif_auto_id, classif_auto_score, classif_auto_when, classif_crossvalidation_id, classif_id, classif_qual, classif_who, classif_when, complement_info, depth_max, depth_min, latitude, longitude, objdate, object_link, objid, objtime, orig_id, random_value, similarity, sunpos"
    img_fields = "file_name, height, imgid, imgrank, objid, orig_file_name, thumb_file_name, thumb_height, thumb_width, width"
    txo_fields = "creation_datetime, creator_email, display_name, id, id_instance, aphia_id, lastupdate_datetime, name, nbrobj, nbrobjcum, parent_id, rename_to, source_desc, source_url, taxostatus, taxotype"
    txp_fields = "aphia_id, name"
    usr_fields = "name, email"
    all_fields = (
        ["sam." + fld.strip() for fld in sam_fields.split(",")]
        + ["acq." + fld.strip() for fld in acq_fields.split(",")]
        + ["obj." + fld.strip() for fld in obj_fields.split(",")]
        + ["img." + fld.strip() for fld in img_fields.split(",")]
        + ["txo." + fld.strip() for fld in txo_fields.split(",")]
        + ["txp." + fld.strip() for fld in txp_fields.split(",")]
        + ["usr." + fld.strip() for fld in usr_fields.split(",")]
    )
    all_fields_txt = ",".join(all_fields)

    def check_ret(details, length):
        for a_det in details:
            assert len(a_det) == length

    objs, details = _prj_query(fastapi, CREATOR_AUTH, prj_id, fields=all_fields_txt)
    check_ret(details, len(all_fields))

    # Test all 'order by', all fields present
    for a_field in all_fields:
        objs, details = _prj_query(
            fastapi, CREATOR_AUTH, prj_id, fields=all_fields_txt, order=a_field
        )
        check_ret(details, len(all_fields))

    # Test all 'order by', single field present
    for a_field in all_fields:
        objs, details = _prj_query(
            fastapi, CREATOR_AUTH, prj_id, fields="obj.objid", order=a_field
        )
        check_ret(details, 1)

    objs, details = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        fields="obj.objid",
        order="img.file_name",
        size=10,
    )
    check_ret(details, 1)

    # Test all 'order by', all fields present and limit
    for a_field in all_fields:
        objs, details = _prj_query(
            fastapi, CREATOR_AUTH, prj_id, fields=all_fields_txt, order=a_field, size=10
        )
        check_ret(details, len(all_fields))

    # Test all 'order by', one field present and limit
    for a_field in all_fields:
        objs, details = _prj_query(
            fastapi, CREATOR_AUTH, prj_id, fields="obj.orig_id", order=a_field, size=10
        )
        check_ret(details, 1)

    # Test with users
    objs, details = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        fields=all_fields_txt,
        order="img.file_name",
        size=10,
        filt_annot="4,3",
    )
    check_ret(details, len(all_fields))

    # Test with project instrument
    objs, details = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        fields=all_fields_txt,
        order="img.file_name",
        size=10,
        instrument="UVP",
    )
    check_ret(details, len(all_fields))

    # Limit AKA size should return exact same data
    objs_no_limit, details_no_limit = _prj_query(
        fastapi, CREATOR_AUTH, prj_id, fields=all_fields_txt, order="usr.name"
    )
    objs_limit, details_limit = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        fields=all_fields_txt,
        order="usr.name",
        size=10000,
    )
    assert objs_no_limit == objs_limit
    assert details_no_limit == details_limit


def test_free_columns(fastapi):
    # Admin imports the project
    prj_id = do_test_import(fastapi, "Free columns Queries test project")
    # Free column in filter
    _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        fields="",
        order=None,
        size=10000,
        samples=590261,
        freetxt="ot01",
        freetxtval="False",
    )


def test_fields_in_body(fastapi):
    prj_id = do_test_import(fastapi, "Queries fields in body test project")
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id)
    some_fields = "obj.orig_id,img.file_name"
    in_qry, details_qry = _prj_query(
        fastapi, CREATOR_AUTH, prj_id, order="obj.objid", fields=some_fields
    )
    assert len(details_qry) > 0
    assert all(len(a_det) == 2 for a_det in details_qry)
    # Same fields in body, no query param
    rsp = fastapi.post(
        url + "?order_field=obj.objid",
        headers=CREATOR_AUTH,
        json={"fields": some_fields},
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["object_ids"] == in_qry
    assert rsp.json()["details"] == details_qry
    # Body wins over query param
    rsp = fastapi.post(
        url + "?order_field=obj.objid&fields=obj.objid",
        headers=CREATOR_AUTH,
        json={"fields": some_fields},
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["details"] == details_qry
    # Body fields alongside real filters, which still apply
    for a_status in ("V", "P"):
        flt_qry, _ = _prj_query(
            fastapi,
            CREATOR_AUTH,
            prj_id,
            order="obj.objid",
            fields="obj.objid",
            statusfilter=a_status,
        )
        rsp = fastapi.post(
            url + "?order_field=obj.objid",
            headers=CREATOR_AUTH,
            json={"fields": "obj.objid", "statusfilter": a_status},
        )
        assert rsp.status_code == status.HTTP_200_OK
        assert rsp.json()["object_ids"] == flt_qry


def test_fields_not_a_filter():
    # Dict and list (sent by frontend) forms
    for body in (
        {"taxo": "1", "fields": "obj.orig_id,fre.area"},
        [["taxo", "1"], ["fields", "obj.orig_id,fre.area"]],
    ):
        flt = ObjectSetQueryFilters.model_validate(body)
        assert flt.fields == "obj.orig_id,fre.area"
        assert "fields" not in flt.base()
        assert flt.base()["taxo"] == "1"
        assert flt.min_base() == {"taxo": "1"}
    assert ObjectSetQueryFilters.model_validate({}).fields is None


def test_fields_in_list_body(fastapi):
    prj_id = do_test_import(fastapi, "Queries fields in list body test project")
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id) + "?order_field=obj.objid"
    ref, ref_details = _prj_query(
        fastapi, CREATOR_AUTH, prj_id, order="obj.objid", fields="obj.orig_id"
    )
    rsp = fastapi.post(
        url, headers=CREATOR_AUTH, json=[["fields", "obj.orig_id"]]
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["object_ids"] == ref
    assert rsp.json()["details"] == ref_details
