# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

from starlette import status

from API_models.filters import ProjectFilters
from API_operations.helpers.Service import Service
from DB.Image import Image
from tests.credentials import CREATOR_AUTH
from tests.test_import import do_test_import, do_import_a_bit_more_skipping

OBJECT_SET_QUERY_URL = "/object_set/{project_id}/query"  # ?order_field={order}&window_start={start}&window_size={size}"


# TODO: Dup/extend of the same in test_classification.py
def _prj_query(
    fastapi,
    auth,
    prj_id,
    order=None,
    start=None,
    size=None,
    fields=None,
    img_order=None,
    **kwargs,
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
    if img_order is not None:
        params.append("img_order=%s" % img_order)
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
    # Both in query param and body: refused, no silent winner
    rsp = fastapi.post(
        url + "?order_field=obj.objid&fields=obj.objid",
        headers=CREATOR_AUTH,
        json={"fields": some_fields},
    )
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "'fields' given both in query string and body" in rsp.json()["detail"]
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
        flt = ProjectFilters.model_validate(body)
        assert flt.fields == "obj.orig_id,fre.area"
        assert "fields" not in flt.base()
        assert flt.base()["taxo"] == "1"
        assert flt.min_base() == {"taxo": "1"}
    assert ProjectFilters.model_validate({}).fields is None


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
    # Both places, list form of body: refused as well
    rsp = fastapi.post(
        url + "&fields=obj.objid", headers=CREATOR_AUTH, json=[["fields", "obj.orig_id"]]
    )
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "'fields'" in rsp.json()["detail"]


def test_query_body_schema_is_project_filters():
    # Generated clients name the body argument after its schema: ProjectFilters gives
    # get_object_set(project_id, project_filters, ...). A subclass would rename it and break callers.
    from main import app

    op = app.openapi()["paths"]["/object_set/{project_id}/query"]["post"]
    schema = op["requestBody"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/ProjectFilters"}


def test_fields_in_body_ignored_elsewhere(fastapi):
    # 'fields' is part of ProjectFilters, but only the query uses it
    from tests.test_classification import OBJECT_SET_SUMMARY_URL

    prj_id = do_test_import(fastapi, "Fields ignored by summary test project")
    url = OBJECT_SET_SUMMARY_URL.format(project_id=prj_id)
    ref = fastapi.post(url, headers=CREATOR_AUTH, json={"statusfilter": "P"})
    assert ref.status_code == status.HTTP_200_OK
    rsp = fastapi.post(
        url, headers=CREATOR_AUTH, json={"statusfilter": "P", "fields": "obj.orig_id"}
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == ref.json()


def test_img_order(fastapi):
    prj_id = do_test_import(fastapi, "Img order test project")

    all_objs, init_details = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        order="obj.objid",
        fields="obj.objid,img.imgid,img.imgrank",
    )
    assert len(all_objs) >= 2
    assert init_details == _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        order="obj.objid",
        fields="obj.objid,img.imgid,img.imgrank",
        img_order=1,
    )[1]

    obj0, obj1 = all_objs[0], all_objs[1]
    with Service() as sce:
        img0 = (
            sce.session.query(Image)
            .filter(Image.objid == obj0)
            .order_by(Image.imgrank)
            .first()
        )
        img1 = (
            sce.session.query(Image)
            .filter(Image.objid == obj1)
            .order_by(Image.imgrank)
            .first()
        )
        assert img0 is not None and img1 is not None
        # Add extra images with non-contiguous imgrank values
        obj0_img2 = Image(
            objid=obj0,
            imgrank=img0.imgrank + 2,
            width=img0.width,
            height=img0.height,
            orig_file_name="obj0_rank2.jpg",
            thumb_width=img0.thumb_width,
            thumb_height=img0.thumb_height,
        )
        obj0_img3 = Image(
            objid=obj0,
            imgrank=img0.imgrank + 5,
            width=img0.width,
            height=img0.height,
            orig_file_name="obj0_rank5.jpg",
            thumb_width=img0.thumb_width,
            thumb_height=img0.thumb_height,
        )
        obj1_img2 = Image(
            objid=obj1,
            imgrank=img1.imgrank + 3,
            width=img1.width,
            height=img1.height,
            orig_file_name="obj1_rank3.jpg",
            thumb_width=img1.thumb_width,
            thumb_height=img1.thumb_height,
        )
        sce.session.add_all([obj0_img2, obj0_img3, obj1_img2])
        sce.session.commit()
        obj0_img2_id, obj0_img2_rank = obj0_img2.imgid, obj0_img2.imgrank
        obj0_img3_id, obj0_img3_rank = obj0_img3.imgid, obj0_img3.imgrank
        obj1_img2_id, obj1_img2_rank = obj1_img2.imgid, obj1_img2.imgrank

    # img_order=2 returns only objects with >= 2 images, picking 2nd by increasing imgrank
    objs_2, details_2 = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        order="obj.objid",
        fields="obj.objid,img.imgid,img.imgrank,img.orig_file_name",
        img_order=2,
    )
    assert objs_2 == [obj0, obj1]
    assert details_2 == [
        [obj0, obj0_img2_id, obj0_img2_rank, "obj0_rank2.jpg"],
        [obj1, obj1_img2_id, obj1_img2_rank, "obj1_rank3.jpg"],
    ]

    # img_order=3 returns only obj0 with its 3rd image
    objs_3, details_3 = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        order="obj.objid",
        fields="obj.objid,img.imgid,img.imgrank,img.orig_file_name",
        img_order=3,
    )
    assert objs_3 == [obj0]
    assert details_3 == [[obj0, obj0_img3_id, obj0_img3_rank, "obj0_rank5.jpg"]]

    # img_order beyond any object's image count returns empty result when img.* requested
    objs_4, details_4 = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        order="obj.objid",
        fields="obj.objid,img.imgid",
        img_order=4,
    )
    assert objs_4 == []
    assert details_4 == []

    # Without img.* fields, img_order does not filter out objects
    objs_no_img, _ = _prj_query(
        fastapi,
        CREATOR_AUTH,
        prj_id,
        order="obj.objid",
        fields="obj.objid",
        img_order=2,
    )
    assert objs_no_img == all_objs

    # img_order < 1 is rejected by validation
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id)
    for bad_order in (0, -1):
        rsp = fastapi.post(
            f"{url}?img_order={bad_order}", headers=CREATOR_AUTH, json={}
        )
        assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def _raw_query(fastapi, prj_id, params: str, **filters) -> dict:
    url = OBJECT_SET_QUERY_URL.format(project_id=prj_id) + params
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=filters)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    return rsp.json()


def test_total_ids_and_parents(fastapi):
    """total_ids is the size of the whole filtered set whatever the window, and parents
    are the ones of each object, either derived from the rows or counted apart."""
    prj_id = do_test_import(fastapi, "Total ids test project")
    do_import_a_bit_more_skipping(fastapi, "Total ids test project")

    full = _raw_query(fastapi, prj_id, "?order_field=obj.objid")
    nb = len(full["object_ids"])
    assert nb == 11
    assert full["total_ids"] == nb
    assert full["project_ids"] == [prj_id] * nb
    # Parents are the ones known by the parents service
    rsp = fastapi.post("/object_set/parents", headers=CREATOR_AUTH, json=full["object_ids"])
    assert rsp.status_code == status.HTTP_200_OK
    parents = rsp.json()
    assert full["acquisition_ids"] == parents["acquisition_ids"]
    assert full["sample_ids"] == parents["sample_ids"]
    assert len(set(full["sample_ids"])) > 1  # the test covers several samples

    def check(params: str, nb_rows: int, total: int = nb, **filters):
        rsp = _raw_query(fastapi, prj_id, params, **filters)
        assert len(rsp["object_ids"]) == nb_rows, params
        assert rsp["total_ids"] == total, params
        # Same parents as in the full query, for the returned objects
        for objid, acq_id, sam_id, prj in zip(
            rsp["object_ids"], rsp["acquisition_ids"], rsp["sample_ids"], rsp["project_ids"]
        ):
            idx = full["object_ids"].index(objid)
            assert (acq_id, sam_id, prj) == (
                full["acquisition_ids"][idx],
                full["sample_ids"][idx],
                prj_id,
            ), params
        return rsp

    order = "&order_field=obj.objid"
    check("?window_size=4" + order, 4)  # A page, the set continues
    check("?window_start=8&window_size=4" + order, 3)  # Last, partial, page
    check("?window_start=4&window_size=7" + order, 7)  # Page ending exactly at the end
    check("?window_start=11&window_size=4" + order, 0)  # Just after the end
    check("?window_start=20&window_size=4" + order, 0)  # Far after the end
    check("?window_start=4" + order, 7)  # Offset only
    check("?window_size=50", nb)  # Window larger than the set, no order
    check("?window_size=0" + order, 0)  # Empty window
    # With a filter, the total is the one of the filtered set
    a_sample = full["sample_ids"][0]
    nb_in_sample = full["sample_ids"].count(a_sample)
    check("?window_size=50" + order, nb_in_sample, nb_in_sample, samples=str(a_sample))
    check("?window_size=1" + order, 1, nb_in_sample, samples=str(a_sample))
    # Image fields, with the image virtual columns
    rsp = check("?window_size=50&fields=img.file_name,obj.objid" + order, nb)
    for (file_name, objid), an_objid in zip(rsp["details"], rsp["object_ids"]):
        assert objid == an_objid
        assert file_name.endswith(".jpg") or file_name.endswith(".png")
    # An image rank which most objects don't have: rows are dropped but the total
    # stays the one of the filtered set, as before.
    rsp = _raw_query(
        fastapi, prj_id, "?window_size=50&img_order=9&fields=img.imgid" + order
    )
    assert rsp["object_ids"] == []
    assert rsp["total_ids"] == nb
