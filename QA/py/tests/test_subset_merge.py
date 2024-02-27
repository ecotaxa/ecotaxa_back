# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import logging

import pytest

# noinspection PyPackageRequirements
from API_models.merge import MergeRsp
from API_models.subset import SubsetReq, SubsetRsp

# Import services
# noinspection PyPackageRequirements
from API_operations.CRUD.Projects import ProjectsService

# noinspection PyPackageRequirements
from API_operations.Consistency import ProjectConsistencyChecker
from API_operations.Merge import MergeService
from API_operations.Subset import SubsetServiceOnProject

# noinspection PyPackageRequirements
from BO.Mappings import ProjectMapping
from DB.Object import ObjectFields

# OK we need a bit of direct DB access
# noinspection PyPackageRequirements
from DB.Project import Project

# noinspection PyPackageRequirements
from deepdiff import DeepDiff

# noinspection PyUnresolvedReferences
from ordered_set import OrderedSet
from starlette import status

from tests.credentials import CREATOR_AUTH, CREATOR_USER_ID
from tests.jobs import (
    wait_for_stable,
    check_job_ok,
    check_job_errors,
    api_wait_for_stable_job,
    api_check_job_errors,
)
from tests.prj_utils import check_project
from tests.test_fastapi import PRJ_CREATE_URL, ADMIN_AUTH, PROJECT_QUERY_URL
from tests.test_import import (
    ADMIN_USER_ID,
    test_import_uvp6,
    DATA_DIR,
    do_import,
    create_project,
    dump_project,
)
from tests.tstlogs_fixture import pushd

OUT_JSON = "out.json"
ORIGIN_AFTER_MERGE_JSON = "out_after_merge.json"
SUBS_AFTER_MERGE_JSON = "out_subs_after_merge.json"
OUT_SUBS_JSON = "out_subs.json"
OUT_MERGE_REMAP_JSON = "out_merge_remap.json"

PROJECT_MERGE_URL = "/projects/{project_id}/merge?source_project_id={source_project_id}&dry_run={dry_run}"

PROJECT_CHECK_URL = "/projects/{project_id}/check"


@pytest.mark.parametrize("prj_id", [-1])
def test_check_project_via_api(prj_id: int, fastapi):
    if prj_id == -1:  # Hack to avoid the need for the test being marked as 'skipped'
        return
    url = PROJECT_CHECK_URL.format(project_id=prj_id)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


# Note: to go faster in a local dev environment, use "filled_database" instead of "database" below
# BUT DON'T COMMIT THE CHANGE
def test_subset_merge_uvp6(database, fastapi, caplog, tstlogs):
    caplog.set_level(logging.ERROR)
    prj_id = test_import_uvp6(database, caplog, "Test Subset Merge")
    check_project(tstlogs, prj_id)
    # Dump the project
    caplog.set_level(logging.DEBUG)
    with open(tstlogs / OUT_JSON, "w") as fd:
        dump_project(ADMIN_USER_ID, prj_id, fd)
    print("\n".join(caplog.messages))

    # Subset in full, i.e. clone
    subset_prj_id = create_project(ADMIN_USER_ID, "Subset of UVP6", "UVP6")
    filters = {"freenum": "n01", "freenumst": "0"}
    params = SubsetReq(
        dest_prj_id=subset_prj_id,
        filters=filters,
        group_type="C",
        limit_type="P",
        limit_value=100.0,
        do_images=True,
    )
    with SubsetServiceOnProject(prj_id=prj_id, req=params) as sce:
        rsp: SubsetRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_ok(job)

    # Dump the subset
    with open(tstlogs / OUT_SUBS_JSON, "w") as fd:
        dump_project(ADMIN_USER_ID, subset_prj_id, fd)

    # Json diff
    with open(tstlogs / OUT_JSON) as fd1:
        json_src = json.load(fd1)
    with open(tstlogs / OUT_SUBS_JSON) as fd2:
        json_subset = json.load(fd2)
    diffs = DeepDiff(json_src, json_subset)
    # Validate by removing all know differences b/w source and subset
    assert "iterable_item_added" not in diffs
    assert "iterable_item_removed" not in diffs
    assert "dictionary_item_added" not in diffs
    assert "dictionary_item_removed" not in diffs
    changed_values = diffs["values_changed"]
    # Title is !=
    del changed_values["root['ttl']"]
    # IDs have changed
    del changed_values["root['samples'][0]['id']"]
    del changed_values["root['samples'][0]['acquisitions'][0]['id']"]
    del changed_values["root['samples'][0]['acquisitions'][0]['processings'][0]['id']"]
    for obj in range(0, 15):
        for img in range(0, 2):
            key = (
                "root['samples'][0]['acquisitions'][0]['objects'][%d]['images'][%d]['fil']"
                % (obj, img)
            )
            del changed_values[key]
    assert changed_values == {}

    # Add a numerical feature into the subset
    with ProjectsService() as sce:
        session = sce.session
        db_prj: Project = session.query(Project).get(subset_prj_id)
        mapg = ProjectMapping().load_from_project(db_prj)
        mapg.add_column(ObjectFields.__tablename__, "object", "foobar", "n")
        db_col = mapg.search_field("object_foobar")
        assert db_col
        mapg.write_to_project(db_prj)
        for a_sample in db_prj.all_samples:
            for an_acquis in a_sample.all_acquisitions:
                for an_obj in an_acquis.all_objects:
                    setattr(an_obj.fields, db_col["field"], 4567)
        session.commit()

    # Re-merge subset into origin project
    # First a dry run to be sure, via API for variety
    url = PROJECT_MERGE_URL.format(
        project_id=prj_id, source_project_id=subset_prj_id, dry_run=True
    )
    response = fastapi.post(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["errors"] == []
    # Then for real
    with pushd(tstlogs):
        with MergeService(
            prj_id=prj_id, src_prj_id=subset_prj_id, dry_run=False
        ) as sce:
            does_it_work: MergeRsp = sce.run(ADMIN_USER_ID)
    assert does_it_work.errors == []

    check_project(tstlogs, prj_id)

    # Dump the subset which should be just gone
    with open(tstlogs / SUBS_AFTER_MERGE_JSON, "w") as fd:
        dump_project(ADMIN_USER_ID, subset_prj_id, fd)
    with open(tstlogs / SUBS_AFTER_MERGE_JSON) as fd:
        json_subset = json.load(fd)
    assert json_subset == {}

    # Dump the origin project which should be 2x larger
    with open(tstlogs / ORIGIN_AFTER_MERGE_JSON, "w") as fd:
        dump_project(ADMIN_USER_ID, prj_id, fd)
    with open(tstlogs / ORIGIN_AFTER_MERGE_JSON) as fd:
        origin_after_merge = json.load(fd)

    # Samples have the same or_ig so they got merged
    diffs = DeepDiff(json_src["samples"][0], origin_after_merge["samples"][0])
    assert "iterable_item_removed" not in diffs
    assert "dictionary_item_removed" not in diffs
    assert "values_changed" not in diffs

    items_added = diffs["iterable_item_added"]
    # Remove image ids which change depending on the run
    for obj in range(15, 30):
        obj_key = "root['acquisitions'][0]['objects'][%d]" % obj
        for img in range(0, 2):
            del items_added[obj_key]["images"][img]["fil"]
    # All objects from subset have been added to the same place
    assert items_added == {
        "root['acquisitions'][0]['objects'][15]": {
            "%area": 95.652,
            "angle": 137.674,
            "area": 207.0,
            "area_exc": 9.0,
            "circ.": 0.516,
            "circex": 0.022428,
            "convarea": 253.0,
            "convarea_area": 1.22222,
            "convperim": 72.0,
            "convperim_perim": 1.01391,
            "cv": 20.3711,
            "depth_max": 194.63,
            "depth_min": 194.63,
            "elongation": 1.85487,
            "fcons": 0.303223,
            "feret": 22.2038,
            "feretareaexc": 7.40127,
            "foobar": 4567.0,
            "fractal": 1.173,
            "height": 18.0,
            "histcum1": 152.0,
            "histcum2": 188.0,
            "histcum3": 218.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 38771.0,
            "kurt": -0.241,
            "kurt_mean": -0.00128671,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 22.11,
            "max": 250.0,
            "mean": 187.3,
            "meanpos": -0.516906,
            "median": 191.0,
            "median_mean": 3.70048,
            "median_mean_range": 0.0201113,
            "min": 66.0,
            "minor": 11.92,
            "mode": 231.0,
            "nb1": 1.0,
            "nb1_area": 0.00483092,
            "nb1_range": 0.00543478,
            "nb2": 2.0,
            "nb2_area": 0.00966184,
            "nb2_range": 0.0108696,
            "nb3": 2.0,
            "nb3_area": 0.00966184,
            "nb3_range": 0.0108696,
            "oid": "20200205-111823_3",
            "perim.": 71.0122,
            "perimareaexc": 23.6707,
            "perimferet": 3.1982,
            "perimmajor": 3.21177,
            "range": 184.0,
            "skelarea": 52.0,
            "skeleton_area": 0.251208,
            "skew": -0.603,
            "skew_mean": -0.00321944,
            "slope": 0.0187593,
            "sr": 20.7364,
            "stddev": 38.155,
            "symetrieh": 5.37,
            "symetrieh_area": 0.025942,
            "symetriehc": 5.563,
            "symetriev": 5.307,
            "symetriev_area": 0.0256377,
            "symetrievc": 5.524,
            "thickr": 1.97315,
            "width": 20.0,
            "x": 29.587,
            "xm": 29.087,
            "y": 27.08,
            "ym": 26.58,
        },
        "root['acquisitions'][0]['objects'][16]": {
            "%area": 99.065,
            "angle": 16.895,
            "area": 107.0,
            "area_exc": 1.0,
            "circ.": 0.432,
            "circex": 0.00404,
            "convarea": 151.0,
            "convarea_area": 1.41121,
            "convperim": 54.0,
            "convperim_perim": 0.96827,
            "cv": 17.9075,
            "depth_max": 195.36,
            "depth_min": 195.36,
            "elongation": 2.10606,
            "fcons": 0.012207,
            "feret": 17.2999,
            "feretareaexc": 17.2999,
            "foobar": 4567.0,
            "fractal": 1.227,
            "height": 12.0,
            "histcum1": 188.0,
            "histcum2": 208.0,
            "histcum3": 221.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 21314.0,
            "kurt": 2.63,
            "kurt_mean": 0.0132031,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 16.939,
            "max": 242.0,
            "mean": 199.196,
            "meanpos": -0.333892,
            "median": 210.0,
            "median_mean": 10.8037,
            "median_mean_range": 0.0631798,
            "min": 71.0,
            "minor": 8.043,
            "mode": 219.0,
            "nb1": 0.0,
            "nb1_area": 0.0,
            "nb1_range": 0.0,
            "nb2": 1.0,
            "nb2_area": 0.00934579,
            "nb2_range": 0.00584795,
            "nb3": 1.0,
            "nb3_area": 0.00934579,
            "nb3_range": 0.00584795,
            "oid": "20200205-111825_1",
            "perim.": 55.7696,
            "perimareaexc": 55.7696,
            "perimferet": 3.22369,
            "perimmajor": 3.29238,
            "range": 171.0,
            "skelarea": 34.0,
            "skeleton_area": 0.317757,
            "skew": -1.711,
            "skew_mean": -0.00858952,
            "slope": 0.0128437,
            "sr": 20.8602,
            "stddev": 35.671,
            "symetrieh": 8.107,
            "symetrieh_area": 0.0757664,
            "symetriehc": 8.322,
            "symetriev": 8.061,
            "symetriev_area": 0.0753364,
            "symetrievc": 8.36,
            "thickr": 1.66667,
            "width": 17.0,
            "x": 25.659,
            "xm": 25.159,
            "y": 18.64,
            "ym": 18.14,
        },
        "root['acquisitions'][0]['objects'][17]": {
            "%area": 95.902,
            "angle": 57.885,
            "area": 122.0,
            "area_exc": 5.0,
            "circ.": 0.587,
            "circex": 0.02405,
            "convarea": 151.0,
            "convarea_area": 1.2377,
            "convperim": 62.0,
            "convperim_perim": 1.21301,
            "cv": 27.8969,
            "depth_max": 195.68,
            "depth_min": 195.68,
            "elongation": 2.35484,
            "fcons": 0.0532227,
            "feret": 19.6979,
            "feretareaexc": 8.80918,
            "foobar": 4567.0,
            "fractal": 1.146,
            "height": 19.0,
            "histcum1": 126.0,
            "histcum2": 155.0,
            "histcum3": 196.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 20012.0,
            "kurt": -0.996,
            "kurt_mean": -0.00607196,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 19.126,
            "max": 240.0,
            "mean": 164.033,
            "meanpos": -0.71645,
            "median": 158.0,
            "median_mean": -6.03279,
            "median_mean_range": -0.0331472,
            "min": 58.0,
            "minor": 8.122,
            "mode": 101.0,
            "nb1": 1.0,
            "nb1_area": 0.00819672,
            "nb1_range": 0.00549451,
            "nb2": 1.0,
            "nb2_area": 0.00819672,
            "nb2_range": 0.00549451,
            "nb3": 1.0,
            "nb3_area": 0.00819672,
            "nb3_range": 0.00549451,
            "oid": "20200205-111826_1",
            "perim.": 51.1127,
            "perimareaexc": 22.8583,
            "perimferet": 2.59483,
            "perimmajor": 2.67242,
            "range": 182.0,
            "skelarea": 23.0,
            "skeleton_area": 0.188525,
            "skew": -0.065,
            "skew_mean": -0.00039626,
            "slope": 0.0103954,
            "sr": 25.1429,
            "stddev": 45.76,
            "symetrieh": 8.578,
            "symetrieh_area": 0.0703115,
            "symetriehc": 8.766,
            "symetriev": 8.545,
            "symetriev_area": 0.070041,
            "symetrievc": 8.799,
            "thickr": 1.78218,
            "width": 14.0,
            "x": 20.377,
            "xm": 19.877,
            "y": 27.689,
            "ym": 27.189,
        },
        "root['acquisitions'][0]['objects'][18]": {
            "%area": 100.0,
            "angle": 104.396,
            "area": 94.0,
            "area_exc": 0.0,
            "circ.": 0.853,
            "circex": 0.0,
            "convarea": 105.0,
            "convarea_area": 1.11702,
            "convperim": 46.0,
            "convperim_perim": 1.23612,
            "cv": 32.626,
            "depth_max": 195.68,
            "depth_min": 195.68,
            "elongation": 1.68693,
            "fcons": 0.0,
            "feret": 14.5604,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.239,
            "height": 15.0,
            "histcum1": 109.0,
            "histcum2": 134.0,
            "histcum3": 198.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 14136.0,
            "kurt": -1.158,
            "kurt_mean": -0.00770034,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 14.209,
            "max": 235.0,
            "mean": 150.383,
            "meanpos": -1.25576,
            "median": 137.0,
            "median_mean": -13.383,
            "median_mean_range": -0.0880459,
            "min": 83.0,
            "minor": 8.423,
            "mode": 232.0,
            "nb1": 0.0,
            "nb1_area": 0.0,
            "nb1_range": 0.0,
            "nb2": 2.0,
            "nb2_area": 0.0212766,
            "nb2_range": 0.0131579,
            "nb3": 1.0,
            "nb3_area": 0.0106383,
            "nb3_range": 0.00657895,
            "oid": "20200205-111826_2",
            "perim.": 37.2132,
            "perimareaexc": 0.0,
            "perimferet": 2.55578,
            "perimmajor": 2.61899,
            "range": 152.0,
            "skelarea": 11.0,
            "skeleton_area": 0.117021,
            "skew": 0.473,
            "skew_mean": 0.0031453,
            "slope": 0.0108728,
            "sr": 32.2789,
            "stddev": 49.064,
            "symetrieh": 7.559,
            "symetrieh_area": 0.0804149,
            "symetriehc": 7.856,
            "symetriev": 7.718,
            "symetriev_area": 0.0821064,
            "symetrievc": 7.782,
            "thickr": 1.85294,
            "width": 10.0,
            "x": 15.245,
            "xm": 14.745,
            "y": 22.298,
            "ym": 21.798,
        },
        "root['acquisitions'][0]['objects'][19]": {
            "%area": 100.0,
            "angle": 88.91,
            "area": 199.0,
            "area_exc": 0.0,
            "circ.": 0.304,
            "circex": 0.0,
            "convarea": 280.0,
            "convarea_area": 1.40704,
            "convperim": 86.0,
            "convperim_perim": 0.948505,
            "cv": 30.4563,
            "depth_max": 195.68,
            "depth_min": 195.68,
            "elongation": 4.4841,
            "fcons": 0.243164,
            "feret": 34.059,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.259,
            "height": 35.0,
            "histcum1": 112.0,
            "histcum2": 148.0,
            "histcum3": 187.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 30326.0,
            "kurt": -1.039,
            "kurt_mean": -0.00681794,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 33.707,
            "max": 234.0,
            "mean": 152.392,
            "meanpos": -0.978608,
            "median": 149.0,
            "median_mean": -3.39196,
            "median_mean_range": -0.0205573,
            "min": 69.0,
            "minor": 7.517,
            "mode": 231.0,
            "nb1": 1.0,
            "nb1_area": 0.00502513,
            "nb1_range": 0.00606061,
            "nb2": 1.0,
            "nb2_area": 0.00502513,
            "nb2_range": 0.00606061,
            "nb3": 2.0,
            "nb3_area": 0.0100503,
            "nb3_range": 0.0121212,
            "oid": "20200205-111826_3",
            "perim.": 90.669,
            "perimareaexc": 0.0,
            "perimferet": 2.66212,
            "perimmajor": 2.68992,
            "range": 165.0,
            "skelarea": 46.0,
            "skeleton_area": 0.231156,
            "skew": 0.157,
            "skew_mean": 0.00103024,
            "slope": 0.016577,
            "sr": 28.1291,
            "stddev": 46.413,
            "symetrieh": 15.148,
            "symetrieh_area": 0.0761206,
            "symetriehc": 15.379,
            "symetriev": 15.163,
            "symetriev_area": 0.076196,
            "symetrievc": 15.425,
            "thickr": 1.59091,
            "width": 10.0,
            "x": 14.872,
            "xm": 14.372,
            "y": 50.962,
            "ym": 50.462,
        },
        "root['acquisitions'][0]['objects'][20]": {
            "%area": 100.0,
            "angle": 38.856,
            "area": 176.0,
            "area_exc": 0.0,
            "circ.": 0.774,
            "circex": 0.0,
            "convarea": 198.0,
            "convarea_area": 1.125,
            "convperim": 62.0,
            "convperim_perim": 1.15984,
            "cv": 53.4118,
            "depth_max": 212.62,
            "depth_min": 212.62,
            "elongation": 1.04145,
            "fcons": 0.617676,
            "feret": 17.2148,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.14,
            "height": 17.0,
            "histcum1": 62.0,
            "histcum2": 121.0,
            "histcum3": 189.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 22322.0,
            "kurt": -1.355,
            "kurt_mean": -0.0106836,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 15.277,
            "max": 234.0,
            "mean": 126.83,
            "meanpos": -0.984755,
            "median": 123.0,
            "median_mean": -3.82955,
            "median_mean_range": -0.0177294,
            "min": 18.0,
            "minor": 14.669,
            "mode": 216.0,
            "nb1": 1.0,
            "nb1_area": 0.00568182,
            "nb1_range": 0.00462963,
            "nb2": 1.0,
            "nb2_area": 0.00568182,
            "nb2_range": 0.00462963,
            "nb3": 1.0,
            "nb3_area": 0.00568182,
            "nb3_range": 0.00462963,
            "oid": "20200205-111908_2",
            "perim.": 53.4558,
            "perimareaexc": 0.0,
            "perimferet": 3.10523,
            "perimmajor": 3.49911,
            "range": 216.0,
            "skelarea": 23.0,
            "skeleton_area": 0.130682,
            "skew": 0.111,
            "skew_mean": 0.00087519,
            "slope": 0.0133572,
            "sr": 31.362,
            "stddev": 67.742,
            "symetrieh": 4.884,
            "symetrieh_area": 0.02775,
            "symetriehc": 5.037,
            "symetriev": 4.957,
            "symetriev_area": 0.0281648,
            "symetrievc": 5.077,
            "thickr": 1.82911,
            "width": 16.0,
            "x": 24.42,
            "xm": 23.92,
            "y": 25.142,
            "ym": 24.642,
        },
        "root['acquisitions'][0]['objects'][21]": {
            "%area": 92.715,
            "angle": 151.894,
            "area": 151.0,
            "area_exc": 11.0,
            "circ.": 0.206,
            "circex": 0.015004,
            "convarea": 222.0,
            "convarea_area": 1.4702,
            "convperim": 74.0,
            "convperim_perim": 0.770972,
            "cv": 8.67776,
            "depth_max": 213.525,
            "depth_min": 213.525,
            "elongation": 2.04966,
            "fcons": 2.53551,
            "feret": 24.3518,
            "feretareaexc": 7.34234,
            "foobar": 4567.0,
            "fractal": 1.172,
            "height": 15.0,
            "histcum1": 208.0,
            "histcum2": 225.0,
            "histcum3": 230.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 33112.0,
            "kurt": 3.315,
            "kurt_mean": 0.0151173,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 19.851,
            "max": 253.0,
            "mean": 219.285,
            "meanpos": -0.400016,
            "median": 226.0,
            "median_mean": 6.71523,
            "median_mean_range": 0.0569087,
            "min": 135.0,
            "minor": 9.685,
            "mode": 231.0,
            "nb1": 0.0,
            "nb1_area": 0.0,
            "nb1_range": 0.0,
            "nb2": 1.0,
            "nb2_area": 0.00662252,
            "nb2_range": 0.00847458,
            "nb3": 1.0,
            "nb3_area": 0.00662252,
            "nb3_range": 0.00847458,
            "oid": "20200205-111910_1",
            "perim.": 95.9828,
            "perimareaexc": 28.9399,
            "perimferet": 3.94151,
            "perimmajor": 4.83516,
            "range": 118.0,
            "skelarea": 69.0,
            "skeleton_area": 0.456954,
            "skew": -1.735,
            "skew_mean": -0.00791209,
            "slope": 0.0324961,
            "sr": 16.1263,
            "stddev": 19.029,
            "symetrieh": 10.109,
            "symetrieh_area": 0.066947,
            "symetriehc": 10.699,
            "symetriev": 10.083,
            "symetriev_area": 0.0667748,
            "symetrievc": 10.725,
            "thickr": 2.18182,
            "width": 24.0,
            "x": 34.725,
            "xm": 34.225,
            "y": 22.719,
            "ym": 22.219,
        },
        "root['acquisitions'][0]['objects'][22]": {
            "%area": 98.889,
            "angle": 98.964,
            "area": 90.0,
            "area_exc": 1.0,
            "circ.": 0.642,
            "circex": 0.007134,
            "convarea": 103.0,
            "convarea_area": 1.14444,
            "convperim": 44.0,
            "convperim_perim": 1.04835,
            "cv": 16.7471,
            "depth_max": 214.165,
            "depth_min": 214.165,
            "elongation": 1.74654,
            "fcons": 0.0,
            "feret": 14.1423,
            "feretareaexc": 14.1423,
            "foobar": 4567.0,
            "fractal": 1.29,
            "height": 15.0,
            "histcum1": 162.0,
            "histcum2": 187.0,
            "histcum3": 213.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 16952.0,
            "kurt": -0.49,
            "kurt_mean": -0.00260146,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 14.147,
            "max": 247.0,
            "mean": 188.356,
            "meanpos": -0.74844,
            "median": 188.0,
            "median_mean": -0.355556,
            "median_mean_range": -0.0025953,
            "min": 110.0,
            "minor": 8.1,
            "mode": 162.0,
            "nb1": 0.0,
            "nb1_area": 0.0,
            "nb1_range": 0.0,
            "nb2": 0.0,
            "nb2_area": 0.0,
            "nb2_range": 0.0,
            "nb3": 2.0,
            "nb3_area": 0.0222222,
            "nb3_range": 0.0145985,
            "oid": "20200205-111912_1",
            "perim.": 41.9706,
            "perimareaexc": 41.9706,
            "perimferet": 2.96773,
            "perimmajor": 2.96675,
            "range": 137.0,
            "skelarea": 19.0,
            "skeleton_area": 0.211111,
            "skew": -0.409,
            "skew_mean": -0.00217143,
            "slope": 0.0107587,
            "sr": 23.0248,
            "stddev": 31.544,
            "symetrieh": 7.928,
            "symetrieh_area": 0.0880889,
            "symetriehc": 8.261,
            "symetriev": 7.983,
            "symetriev_area": 0.0887,
            "symetrievc": 8.317,
            "thickr": 1.70886,
            "width": 9.0,
            "x": 13.256,
            "xm": 12.756,
            "y": 22.778,
            "ym": 22.278,
        },
        "root['acquisitions'][0]['objects'][23]": {
            "%area": 100.0,
            "angle": 133.602,
            "area": 158.0,
            "area_exc": 0.0,
            "circ.": 0.852,
            "circex": 0.0,
            "convarea": 173.0,
            "convarea_area": 1.09494,
            "convperim": 60.0,
            "convperim_perim": 1.24264,
            "cv": 44.9096,
            "depth_max": 215.415,
            "depth_min": 215.415,
            "elongation": 1.23186,
            "fcons": 0.927734,
            "feret": 16.4583,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.139,
            "height": 16.0,
            "histcum1": 83.0,
            "histcum2": 119.0,
            "histcum3": 181.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 20924.0,
            "kurt": -1.09,
            "kurt_mean": -0.00823074,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 15.742,
            "max": 234.0,
            "mean": 132.43,
            "meanpos": -0.82289,
            "median": 122.0,
            "median_mean": -10.4304,
            "median_mean_range": -0.0463572,
            "min": 9.0,
            "minor": 12.779,
            "mode": 93.0,
            "nb1": 1.0,
            "nb1_area": 0.00632911,
            "nb1_range": 0.00444444,
            "nb2": 1.0,
            "nb2_area": 0.00632911,
            "nb2_range": 0.00444444,
            "nb3": 1.0,
            "nb3_area": 0.00632911,
            "nb3_range": 0.00444444,
            "oid": "20200205-111915_1",
            "perim.": 48.2843,
            "perimareaexc": 0.0,
            "perimferet": 2.93374,
            "perimmajor": 3.06723,
            "range": 225.0,
            "skelarea": 22.0,
            "skeleton_area": 0.139241,
            "skew": 0.25,
            "skew_mean": 0.00188778,
            "slope": 0.013127,
            "sr": 26.4329,
            "stddev": 59.474,
            "symetrieh": 4.915,
            "symetrieh_area": 0.0311076,
            "symetriehc": 5.168,
            "symetriev": 5.035,
            "symetriev_area": 0.0318671,
            "symetrievc": 5.168,
            "thickr": 1.53383,
            "width": 16.0,
            "x": 24.006,
            "xm": 23.506,
            "y": 23.842,
            "ym": 23.342,
        },
        "root['acquisitions'][0]['objects'][24]": {
            "%area": 100.0,
            "angle": 51.174,
            "area": 163.0,
            "area_exc": 0.0,
            "circ.": 0.733,
            "circex": 0.0,
            "convarea": 186.0,
            "convarea_area": 1.1411,
            "convperim": 58.0,
            "convperim_perim": 1.09703,
            "cv": 33.632,
            "depth_max": 215.76,
            "depth_min": 215.76,
            "elongation": 1.34347,
            "fcons": 0.0,
            "feret": 18.6562,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.189,
            "height": 15.0,
            "histcum1": 107.0,
            "histcum2": 147.0,
            "histcum3": 189.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 24356.0,
            "kurt": -1.113,
            "kurt_mean": -0.00744864,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 16.698,
            "max": 235.0,
            "mean": 149.423,
            "meanpos": -0.827441,
            "median": 148.0,
            "median_mean": -1.42331,
            "median_mean_range": -0.00753076,
            "min": 46.0,
            "minor": 12.429,
            "mode": 112.0,
            "nb1": 0.0,
            "nb1_area": 0.0,
            "nb1_range": 0.0,
            "nb2": 2.0,
            "nb2_area": 0.0122699,
            "nb2_range": 0.010582,
            "nb3": 1.0,
            "nb3_area": 0.00613497,
            "nb3_range": 0.00529101,
            "oid": "20200205-111916_1",
            "perim.": 52.8701,
            "perimareaexc": 0.0,
            "perimferet": 2.83391,
            "perimmajor": 3.16625,
            "range": 189.0,
            "skelarea": 18.0,
            "skeleton_area": 0.110429,
            "skew": 0.109,
            "skew_mean": 0.00072947,
            "slope": 0.0124102,
            "sr": 26.5894,
            "stddev": 50.254,
            "symetrieh": 4.776,
            "symetrieh_area": 0.0293006,
            "symetriehc": 4.929,
            "symetriev": 4.715,
            "symetriev_area": 0.0289264,
            "symetrievc": 4.887,
            "thickr": 1.89781,
            "width": 16.0,
            "x": 25.126,
            "xm": 24.626,
            "y": 23.248,
            "ym": 22.748,
        },
        "root['acquisitions'][0]['objects'][25]": {
            "%area": 100.0,
            "angle": 71.812,
            "area": 119.0,
            "area_exc": 0.0,
            "circ.": 0.856,
            "circex": 0.0,
            "convarea": 131.0,
            "convarea_area": 1.10084,
            "convperim": 52.0,
            "convperim_perim": 1.24405,
            "cv": 44.7217,
            "depth_max": 215.76,
            "depth_min": 215.76,
            "elongation": 1.58053,
            "fcons": 0.0583496,
            "feret": 15.0538,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.187,
            "height": 16.0,
            "histcum1": 83.0,
            "histcum2": 115.0,
            "histcum3": 176.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 15628.0,
            "kurt": -1.028,
            "kurt_mean": -0.00782775,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 15.475,
            "max": 235.0,
            "mean": 131.328,
            "meanpos": -0.876145,
            "median": 117.0,
            "median_mean": -14.3277,
            "median_mean_range": -0.0645393,
            "min": 13.0,
            "minor": 9.791,
            "mode": 77.0,
            "nb1": 0.0,
            "nb1_area": 0.0,
            "nb1_range": 0.0,
            "nb2": 1.0,
            "nb2_area": 0.00840336,
            "nb2_range": 0.0045045,
            "nb3": 1.0,
            "nb3_area": 0.00840336,
            "nb3_range": 0.0045045,
            "oid": "20200205-111916_2",
            "perim.": 41.799,
            "perimareaexc": 0.0,
            "perimferet": 2.77665,
            "perimmajor": 2.70107,
            "range": 222.0,
            "skelarea": 15.0,
            "skeleton_area": 0.12605,
            "skew": 0.298,
            "skew_mean": 0.00226913,
            "slope": 0.0107428,
            "sr": 26.4559,
            "stddev": 58.732,
            "symetrieh": 6.752,
            "symetrieh_area": 0.0567395,
            "symetriehc": 6.811,
            "symetriev": 6.727,
            "symetriev_area": 0.0565294,
            "symetrievc": 6.811,
            "thickr": 1.60494,
            "width": 12.0,
            "x": 18.105,
            "xm": 17.605,
            "y": 23.996,
            "ym": 23.496,
        },
        "root['acquisitions'][0]['objects'][26]": {
            "%area": 96.35,
            "angle": 92.031,
            "area": 137.0,
            "area_exc": 5.0,
            "circ.": 0.312,
            "circex": 0.011374,
            "convarea": 194.0,
            "convarea_area": 1.41606,
            "convperim": 66.0,
            "convperim_perim": 0.887981,
            "cv": 6.58822,
            "depth_max": 224.44,
            "depth_min": 224.44,
            "elongation": 1.64962,
            "fcons": 0.924723,
            "feret": 19.9244,
            "feretareaexc": 8.91045,
            "foobar": 4567.0,
            "fractal": 1.161,
            "height": 19.0,
            "histcum1": 207.0,
            "histcum2": 220.0,
            "histcum3": 228.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 29961.0,
            "kurt": 0.047,
            "kurt_mean": 0.00021491,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 16.963,
            "max": 247.0,
            "mean": 218.693,
            "meanpos": -0.581322,
            "median": 221.0,
            "median_mean": 2.30657,
            "median_mean_range": 0.0299555,
            "min": 170.0,
            "minor": 10.283,
            "mode": 231.0,
            "nb1": 0.0,
            "nb1_area": 0.0,
            "nb1_range": 0.0,
            "nb2": 1.0,
            "nb2_area": 0.00729927,
            "nb2_range": 0.012987,
            "nb3": 1.0,
            "nb3_area": 0.00729927,
            "nb3_range": 0.012987,
            "oid": "20200205-111938_15",
            "perim.": 74.3259,
            "perimareaexc": 33.2396,
            "perimferet": 3.7304,
            "perimmajor": 4.38165,
            "range": 77.0,
            "skelarea": 45.0,
            "skeleton_area": 0.328467,
            "skew": -0.674,
            "skew_mean": -0.00308194,
            "slope": 0.0252888,
            "sr": 18.7117,
            "stddev": 14.408,
            "symetrieh": 7.391,
            "symetrieh_area": 0.0539489,
            "symetriehc": 7.872,
            "symetriev": 7.58,
            "symetriev_area": 0.0553285,
            "symetrievc": 7.894,
            "thickr": 2.19835,
            "width": 16.0,
            "x": 24.31,
            "xm": 23.81,
            "y": 29.529,
            "ym": 29.029,
        },
        "root['acquisitions'][0]['objects'][27]": {
            "%area": 100.0,
            "angle": 24.012,
            "area": 93.0,
            "area_exc": 0.0,
            "circ.": 0.501,
            "circex": 0.0,
            "convarea": 113.0,
            "convarea_area": 1.21505,
            "convperim": 52.0,
            "convperim_perim": 1.07696,
            "cv": 20.262,
            "depth_max": 252.235,
            "depth_min": 252.235,
            "elongation": 2.10835,
            "fcons": 0.0598958,
            "feret": 17.8887,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.203,
            "height": 11.0,
            "histcum1": 163.0,
            "histcum2": 187.0,
            "histcum3": 211.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 17229.0,
            "kurt": 2.105,
            "kurt_mean": 0.0113625,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 15.8,
            "max": 232.0,
            "mean": 185.258,
            "meanpos": -0.330897,
            "median": 190.0,
            "median_mean": 4.74194,
            "median_mean_range": 0.0252231,
            "min": 44.0,
            "minor": 7.494,
            "mode": 220.0,
            "nb1": 1.0,
            "nb1_area": 0.0107527,
            "nb1_range": 0.00531915,
            "nb2": 1.0,
            "nb2_area": 0.0107527,
            "nb2_range": 0.00531915,
            "nb3": 2.0,
            "nb3_area": 0.0215054,
            "nb3_range": 0.0106383,
            "oid": "20200205-112050_1",
            "perim.": 48.2843,
            "perimareaexc": 0.0,
            "perimferet": 2.69914,
            "perimmajor": 3.05597,
            "range": 188.0,
            "skelarea": 19.0,
            "skeleton_area": 0.204301,
            "skew": -1.332,
            "skew_mean": -0.00718997,
            "slope": 0.014663,
            "sr": 19.9665,
            "stddev": 37.537,
            "symetrieh": 9.446,
            "symetrieh_area": 0.10157,
            "symetriehc": 9.769,
            "symetriev": 9.468,
            "symetriev_area": 0.101806,
            "symetrievc": 9.737,
            "thickr": 2.14925,
            "width": 17.0,
            "x": 24.36,
            "xm": 23.86,
            "y": 16.274,
            "ym": 15.774,
        },
        "root['acquisitions'][0]['objects'][28]": {
            "%area": 90.909,
            "angle": 69.209,
            "area": 165.0,
            "area_exc": 15.0,
            "circ.": 0.43,
            "circex": 0.039107,
            "convarea": 231.0,
            "convarea_area": 1.4,
            "convperim": 68.0,
            "convperim_perim": 0.979454,
            "cv": 13.9825,
            "depth_max": 253.615,
            "depth_min": 253.615,
            "elongation": 2.0967,
            "fcons": 0.548584,
            "feret": 21.5455,
            "feretareaexc": 5.56303,
            "foobar": 4567.0,
            "fractal": 1.189,
            "height": 21.0,
            "histcum1": 192.0,
            "histcum2": 215.0,
            "histcum3": 225.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 34533.0,
            "kurt": 3.826,
            "kurt_mean": 0.0182808,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 20.988,
            "max": 249.0,
            "mean": 209.291,
            "meanpos": -0.302451,
            "median": 220.0,
            "median_mean": 10.7091,
            "median_mean_range": 0.0626263,
            "min": 78.0,
            "minor": 10.01,
            "mode": 220.0,
            "nb1": 1.0,
            "nb1_area": 0.00606061,
            "nb1_range": 0.00584795,
            "nb2": 1.0,
            "nb2_area": 0.00606061,
            "nb2_range": 0.00584795,
            "nb3": 1.0,
            "nb3_area": 0.00606061,
            "nb3_range": 0.00584795,
            "oid": "20200205-112053_1",
            "perim.": 69.4264,
            "perimareaexc": 17.9258,
            "perimferet": 3.22231,
            "perimmajor": 3.30791,
            "range": 171.0,
            "skelarea": 59.0,
            "skeleton_area": 0.357576,
            "skew": -1.789,
            "skew_mean": -0.00854791,
            "slope": 0.0245644,
            "sr": 17.1135,
            "stddev": 29.264,
            "symetrieh": 7.409,
            "symetrieh_area": 0.044903,
            "symetriehc": 7.597,
            "symetriev": 7.433,
            "symetriev_area": 0.0450485,
            "symetrievc": 7.639,
            "thickr": 2.13265,
            "width": 15.0,
            "x": 22.712,
            "xm": 22.212,
            "y": 30.773,
            "ym": 30.273,
        },
        "root['acquisitions'][0]['objects'][29]": {
            "%area": 100.0,
            "angle": 53.112,
            "area": 360.0,
            "area_exc": 0.0,
            "circ.": 0.708,
            "circex": 0.0,
            "convarea": 396.0,
            "convarea_area": 1.1,
            "convperim": 92.0,
            "convperim_perim": 1.15127,
            "cv": 46.0034,
            "depth_max": 255.44,
            "depth_min": 255.44,
            "elongation": 1.50602,
            "fcons": 0.185059,
            "feret": 26.077,
            "feretareaexc": 0.0,
            "foobar": 4567.0,
            "fractal": 1.059,
            "height": 25.0,
            "histcum1": 80.0,
            "histcum2": 99.0,
            "histcum3": 171.0,
            "images": [{"rnk": 1}, {"rnk": 100}],
            "intden": 44722.0,
            "kurt": -0.9,
            "kurt_mean": -0.00724476,
            "latitude": 43.0,
            "longitude": 17.0,
            "major": 26.274,
            "max": 235.0,
            "mean": 124.228,
            "meanpos": -1.21424,
            "median": 101.0,
            "median_mean": -23.2278,
            "median_mean_range": -0.114989,
            "min": 33.0,
            "minor": 17.446,
            "mode": 91.0,
            "nb1": 2.0,
            "nb1_area": 0.00555556,
            "nb1_range": 0.00990099,
            "nb2": 1.0,
            "nb2_area": 0.00277778,
            "nb2_range": 0.0049505,
            "nb3": 1.0,
            "nb3_area": 0.00277778,
            "nb3_range": 0.0049505,
            "oid": "20200205-112059_1",
            "perim.": 79.9117,
            "perimareaexc": 0.0,
            "perimferet": 3.06445,
            "perimmajor": 3.04147,
            "range": 202.0,
            "skelarea": 30.0,
            "skeleton_area": 0.0833333,
            "skew": 0.658,
            "skew_mean": 0.00529672,
            "slope": 0.0251467,
            "sr": 28.2916,
            "stddev": 57.149,
            "symetrieh": 4.563,
            "symetrieh_area": 0.012675,
            "symetriehc": 4.626,
            "symetriev": 4.632,
            "symetriev_area": 0.0128667,
            "symetrievc": 4.613,
            "thickr": 1.72065,
            "width": 23.0,
            "x": 34.944,
            "xm": 34.444,
            "y": 38.022,
            "ym": 37.522,
        },
    }

    # changed_values = diffs['values_changed']
    # IDs have changed
    # del changed_values["root['id']"]  # root is the sample
    # del changed_values["root['acquisitions'][0]['id']"]
    # del changed_values["root['acquisitions'][0]['id']"]
    # for obj in range(0, 15):
    #     for img in range(0, 2):
    #         key = "root['acquisitions'][0]['objects'][%d]['images'][%d]['fil']" % \
    #               (obj, img)
    #         del changed_values[key]
    # assert changed_values == {}
    # # New feature appeared
    # added_values = diffs['dictionary_item_added']
    # for obj in range(0, 15):
    #     key = "root['acquisitions'][0]['objects'][%d]['foobar']" % obj
    #     added_values.remove(key)
    # assert added_values == {}


MERGE_DIR_1 = DATA_DIR / "merge_test" / "lots_of_cols"
MERGE_DIR_2 = DATA_DIR / "merge_test" / "more_cols"
MERGE_DIR_3 = DATA_DIR / "merge_test" / "even_more_cols"
MERGE_DIR_4 = DATA_DIR / "merge_test" / "second_merge"


def test_merge_remap(fastapi, caplog, tstlogs):
    # Project 1, usual columns
    prj_id = create_project(CREATOR_USER_ID, "Merge Dest project")
    do_import(prj_id, MERGE_DIR_1, CREATOR_USER_ID)
    check_project(tstlogs, prj_id)
    # Project 2, same columns but different order
    # acq: remove acq_magnification and swap the 2 others
    # process: remove process_stop_n_images & process_gamma_value, put process_software at the end
    # sample: rename sample_volconc to sample_volconc2 and move it in last
    # object: remove object_link object_cv and object_sr, move lat & lon near the end
    prj_id2 = create_project(CREATOR_USER_ID, "Merge Src project")
    do_import(prj_id2, MERGE_DIR_2, CREATOR_USER_ID)
    check_project(tstlogs, prj_id2)
    # Merge
    url = PROJECT_MERGE_URL.format(
        project_id=prj_id, source_project_id=prj_id2, dry_run=False
    )
    response = fastapi.post(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["errors"] == []
    # Dump the dest
    with open(tstlogs / OUT_MERGE_REMAP_JSON, "w") as fd:
        dump_project(ADMIN_USER_ID, prj_id, fd)
    # Grab all median_mean free col values
    all_lats = []
    with open(tstlogs / OUT_MERGE_REMAP_JSON) as fd:
        for a_line in fd.readlines():
            if "median_mean" in a_line:
                a_line = a_line.strip().strip(",")
                all_lats.append(a_line)
    expected = ['"median_mean": 5555.0' for _n in range(11)]
    assert len(all_lats) == len(expected)
    assert all_lats == expected
    # Project 3 mistake as it has nothing to do with the 2 first ones
    prj_id3 = create_project(CREATOR_USER_ID, "Merge Src Big project")
    do_import(prj_id3, MERGE_DIR_3, CREATOR_USER_ID)
    check_project(tstlogs, prj_id3)
    url = PROJECT_MERGE_URL.format(
        project_id=prj_id, source_project_id=prj_id3, dry_run=False
    )
    response = fastapi.post(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["errors"] == [
        "Column 'samples.5comment' cannot be mapped. No space left in mapping.",
        "Column 'samples.5volconc2' cannot be mapped. No space left in mapping.",
    ]
    # Project 4 is different but compatible
    # It has a new acquisition for an existing sample
    prj_id4 = create_project(CREATOR_USER_ID, "Merge Src small project")
    do_import(prj_id4, MERGE_DIR_4, CREATOR_USER_ID)
    check_project(tstlogs, prj_id4)
    url = PROJECT_MERGE_URL.format(
        project_id=prj_id, source_project_id=prj_id4, dry_run=False
    )
    response = fastapi.post(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["errors"] == []


def test_empty_subset_uvp6(database, fastapi, caplog):
    with caplog.at_level(logging.ERROR):
        prj_id = test_import_uvp6(database, caplog, "Test empty Subset")

    subset_prj_id = create_project(ADMIN_USER_ID, "Empty subset")
    # OK this test is just for covering the code in filters
    filters: ProjectFilters = {
        "taxo": "23456",
        "taxochild": "Y",
        "statusfilter": "V",
        "MapN": "40",
        "MapW": "45",
        "MapE": "50",
        "MapS": "55",
        "depthmin": "10",
        "depthmax": "40",
        "samples": "1,3,4",
        "instrum": "inst",
        "daytime": "A",
        "month": "5",
        "fromdate": "2020-05-01",
        "todate": "2020-05-31",
        "fromtime": "14:34:01",
        "totime": "15:34",
        "inverttime": "1",
        "validfromdate": "2020-05-01 12:00",
        "validtodate": "2020-05-01 18:00",
        "freenum": "n01",
        "freenumst": "0",
        "freenumend": "999999",
        "freetxt": "p01",
        "freetxtval": "zooprocess",
        "filt_annot": "34,67",
    }
    params = SubsetReq(
        dest_prj_id=subset_prj_id,
        filters=filters,
        group_type="C",
        limit_type="P",
        limit_value=100.0,
        do_images=True,
    )
    with SubsetServiceOnProject(prj_id=prj_id, req=params) as sce:
        rsp: SubsetRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    errors = check_job_errors(job)
    assert errors == ["No object found to clone into subset."]
    # A bit of fastapi testing
    # TODO for #484: Ensure it's a 200 for dst_prj_id and a non-admin user
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK


def test_empty_subset_uvp6_other(database, fastapi, caplog):
    with caplog.at_level(logging.ERROR):
        prj_id = test_import_uvp6(database, caplog, "Test empty Subset")

    subset_prj_id = create_project(ADMIN_USER_ID, "Empty subset")
    # OK this test is just for covering (more) the code in filters
    filters: ProjectFilters = {
        "taxo": "23456",
        "taxochild": "N",
        "statusfilter": "NVW",
        "MapN": "40",
        "MapW": "45",
        "MapE": "50",
        "MapS": "55",
        "depthmin": "10",
        "depthmax": "40",
        "samples": "1,3,4",
        "instrum": "inst",
        "daytime": "A",
        "month": "5",
        "fromdate": "2020-05-01",
        "todate": "2020-05-31",
        "fromtime": "14:34:01",
        "totime": "15:34",
        "inverttime": "0",
        "validfromdate": "2020-05-01 12:00",
        "validtodate": "2020-05-01 18:00",
        "freenum": "n01",
        "freenumst": "0",
        "freenumend": "999999",
        "freetxt": "s01",
        "freetxtval": "zooprocess",
        "filt_last_annot": "34,67",
    }
    params = SubsetReq(
        dest_prj_id=subset_prj_id,
        filters=filters,
        group_type="C",
        limit_type="P",
        limit_value=100.0,
        do_images=True,
    )
    with SubsetServiceOnProject(prj_id=prj_id, req=params) as sce:
        rsp: SubsetRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    errors = check_job_errors(job)
    assert errors == ["No object found to clone into subset."]
    # A bit of fastapi testing
    # TODO for #484: Ensure it's a 200 for dst_prj_id and a non-admin user
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK


SUBSET_URL = "/projects/{project_id}/subset"


def test_api_subset(fastapi, caplog):
    # Subset a fresh project, why not?
    # Create an empty project
    url1 = PRJ_CREATE_URL
    res = fastapi.post(url1, headers=ADMIN_AUTH, json={"title": "API subset src test"})
    src_prj_id = res.json()
    res = fastapi.post(url1, headers=ADMIN_AUTH, json={"title": "API subset tgt test"})
    tgt_prj_id = res.json()

    url = SUBSET_URL.format(project_id=src_prj_id)
    req = {
        "dest_prj_id": tgt_prj_id,
        "group_type": "A",
        "limit_type": "P",
        "limit_value": 10,
        "do_images": True,
    }
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    job_id = rsp.json()["job_id"]
    job = api_wait_for_stable_job(fastapi, job_id)
    errors = api_check_job_errors(fastapi, job_id)
    assert errors == ["No object found to clone into subset."]

    test_check_project_via_api(tgt_prj_id, fastapi)


def test_subset_of_no_visible_issue_484(fastapi, caplog):
    # https://github.com/oceanomics/ecotaxa_dev/issues/484
    # First found as a subset of subset failed
    url1 = PRJ_CREATE_URL
    res = fastapi.post(
        url1,
        headers=CREATOR_AUTH,
        json={"title": "API subset src test", "visible": False},
    )
    src_prj_id = res.json()
    res = fastapi.post(
        url1,
        headers=CREATOR_AUTH,
        json={"title": "API subset tgt test", "visible": False},
    )
    tgt_prj_id = res.json()

    url = SUBSET_URL.format(project_id=src_prj_id)
    req = {
        "dest_prj_id": tgt_prj_id,
        "group_type": "A",
        "limit_type": "P",
        "limit_value": 10,
        "do_images": True,
    }
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    job_id = rsp.json()["job_id"]
    job = api_wait_for_stable_job(fastapi, job_id)
    errors = api_check_job_errors(fastapi, job_id)
    assert errors == ["No object found to clone into subset."]

    test_check_project_via_api(tgt_prj_id, fastapi)


def test_subset_consistency(database, caplog, tstlogs):
    caplog.set_level(logging.ERROR)
    from tests.test_import import import_plain

    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Import update")
    # Plain import first
    import_plain(prj_id)
    check_project(tstlogs, prj_id)
    # Dump the project
    caplog.set_level(logging.DEBUG)
    with open(tstlogs / OUT_JSON, "w") as fd:
        dump_project(ADMIN_USER_ID, prj_id, fd)
    print("\n".join(caplog.messages))

    # Subset in full, i.e. clone
    subset_prj_id = create_project(ADMIN_USER_ID, "Subset of")
    filters = {"freenum": "n01", "freenumst": "0"}
    params = SubsetReq(
        dest_prj_id=subset_prj_id,
        filters=filters,
        group_type="S",
        limit_type="P",
        limit_value=100.0,
        do_images=True,
    )
    with SubsetServiceOnProject(prj_id=prj_id, req=params) as sce:
        rsp: SubsetRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_ok(job)
    check_project(tstlogs, subset_prj_id)
