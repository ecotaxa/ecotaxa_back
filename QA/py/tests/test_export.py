import datetime
import json
import logging
from typing import Dict, Any
from unittest import mock

from deepdiff import DeepDiff
from deepdiff.helper import TREE_VIEW

# noinspection PyPackageRequirements
from starlette import status

from tests.credentials import (
    ADMIN_AUTH,
    ADMIN_USER_ID,
    CREATOR_AUTH,
    ORDINARY_USER_USER_ID,
    USER_AUTH,
)
from tests.export_shared import download_and_unzip_and_check, download_and_check
from tests.jobs import (
    JOB_QUERY_URL,
    wait_for_stable,
    api_check_job_ok,
    get_job_and_wait_until_ok,
)
from tests.test_classification import (
    classify_all,
    query_all_objects,
    copepod_id,
    crustacea,
)
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import create_project, do_import, DATA_DIR, dump_project
from tests.test_import_update import do_import_update
from tests.test_update_prj import PROJECT_UPDATE_URL

OBJECT_SET_EXPORT_URL = "/object_set/export"

_req_tmpl = {
    "exp_type": "TSV",
    "tsv_entities": "OPASHC",
    "coma_as_separator": False,
    "format_dates_times": False,
    "with_images": False,
    "only_first_image": False,
    "split_by": "sample",
    "with_internal_ids": False,
    "out_to_ftp": False,
    "sum_subtotal": "",
}

BAK_EXP_TMPL = {
    "exp_type": "BAK",
    "tsv_entities": "OPASHC",
    "coma_as_separator": False,
    "format_dates_times": True,
    "with_images": True,
    "only_first_image": False,
    "split_by": "sample",
    "with_internal_ids": False,
    "out_to_ftp": True,
    "sum_subtotal": "",
}


def test_export_tsv(database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping

    prj_id = test_import(database, caplog, "TSV export project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(database, caplog, "TSV export project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    _prj_json = rsp.json()

    caplog.set_level(logging.DEBUG)

    # Admin exports it
    url = OBJECT_SET_EXPORT_URL
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id})
    req_and_filters = {"filters": filters, "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "tsv_all_entities_no_img_no_ids")

    # Backup export
    req.update({"exp_type": "BAK", "with_images": True, "only_first_image": False})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_all_images")

    # Backup export without images (but their ref is still in the TSVs)
    req.update({"exp_type": "BAK", "with_images": False, "only_first_image": False})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_no_image")

    # DOI export
    req.update({"exp_type": "DOI"})
    fixed_date = datetime.datetime(2021, 5, 30, 11, 22, 33)
    with mock.patch("helpers.DateTime._now_time", return_value=fixed_date):
        rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
        assert rsp.status_code == status.HTTP_200_OK
        _job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # The object_id inside prevents predictability
    # TODO: Better comparison ignoring columns, inject project id and so on
    # download_and_unzip_and_check(fastapi, job_id, "doi", only_hdr=True)

    # TSV export with IDs
    req.update(
        {
            "exp_type": "TSV",
            "with_internal_ids": True,
            "out_to_ftp": True,
            "coma_as_separator": True,
        }
    )
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # Too much randomness inside: IDs, random value
    # TODO: Better comparison ignoring columns
    download_and_unzip_and_check(fastapi, job_id, "tsv_with_ids", only_hdr=True)

    # Summary export, 3 types
    req.update({"exp_type": "SUM", "out_to_ftp": True, "sum_subtotal": "S"})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_sample", only_hdr=True)

    req.update({"exp_type": "SUM", "out_to_ftp": True, "sum_subtotal": "A"})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_subsample", only_hdr=True)

    req.update({"exp_type": "SUM", "out_to_ftp": True, "sum_subtotal": ""})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_whole", only_hdr=True)


def test_export_roundtrip(database, fastapi, caplog, tstlogs):
    """roundtrip export/import other/compare"""
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import_uvp6

    prj_id = test_import_uvp6(
        database, caplog, "TSV UVP6 roundtrip export source project"
    )

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    _prj_json = rsp.json()

    # Admin exports it
    url = OBJECT_SET_EXPORT_URL
    req = dict(BAK_EXP_TMPL, **{"project_id": prj_id})
    req_and_filters = {"filters": {}, "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    file_in_ftp = job_dict["result"]["out_file"]

    # Create a clone project
    clone_prj_id = create_project(
        ADMIN_USER_ID, "TSV UVP6 roundtrip export clone project"
    )
    do_import(
        clone_prj_id,
        source_path=DATA_DIR / "ftp" / ("task_%d_%s" % (job_id, file_in_ftp)),
        user_id=ADMIN_USER_ID,
    )
    changes = diff_projects(
        prj_id, "exp_source.json", clone_prj_id, "exp_clone.json", tstlogs
    )
    assert len(changes) == 1
    assert changes[0].path() == "root['ttl']"  # Just title changed


def force_leaves(prj_json: Dict, forced: Dict[str, Any]):
    """Force values on leaf nodes"""
    if isinstance(prj_json, list):
        for node in prj_json:
            force_leaves(node, forced)
    else:
        for k in prj_json.keys():
            v = prj_json[k]
            if k in forced and type(v) == type(forced[k]):
                prj_json[k] = forced[k]
                continue
            if isinstance(v, (list, dict)):
                force_leaves(v, forced)


def diff_projects(
    ref_prj_id: int, ref_prj_dump: str, other_prj_id: int, other_prj_dump: str, tstlogs
):
    jsons = []
    for prj_id, dump in zip((ref_prj_id, other_prj_id), (ref_prj_dump, other_prj_dump)):
        prj_json = json_dump_project(prj_id, dump, tstlogs)
        force_leaves(
            prj_json, {"id": 0, "fil": "xx.png"}
        )  # IDs and file names are unpredictable
        jsons.append(prj_json)
    diffs = DeepDiff(jsons[0], jsons[1], view=TREE_VIEW)
    assert "iterable_item_added" not in diffs
    assert "iterable_item_removed" not in diffs
    assert "dictionary_item_added" not in diffs
    assert "dictionary_item_removed" not in diffs
    changed_values = diffs["values_changed"]
    return changed_values


def json_dump_project(prj_id, dump_file, tstlogs):
    with open(tstlogs / dump_file, "w") as fd:
        dump_project(ADMIN_USER_ID, prj_id, fd)
    with open(tstlogs / dump_file, "r") as fd:
        prj_json = json.load(fd)
    return prj_json


def test_export_roundtrip_self(database, fastapi, caplog, tstlogs):
    """Roundtrip export/validates/import self
    Scenario: Someone saves a validated project's classifs and wants to restore it to saved state.
    """
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import_uvp6

    prj_id = test_import_uvp6(
        database, caplog, "TSV UVP6 roundtrip classifs export source project"
    )

    # Grant rights to another annotator
    qry_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(qry_url, headers=ADMIN_AUTH)
    read_json = rsp.json()
    usr = {"id": ORDINARY_USER_USER_ID, "email": "ignored", "name": "see email"}
    read_json["annotators"].append(usr)
    upd_url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(upd_url, headers=ADMIN_AUTH, json=read_json)
    assert rsp.status_code == status.HTTP_200_OK

    # Classify-validate all
    obj_ids = query_all_objects(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 15

    def classify_validate_all(who, switch: bool = False):
        classify_all(fastapi, obj_ids[0 if switch else 1 :: 2], copepod_id, who)
        classify_all(fastapi, obj_ids[1 if switch else 0 :: 2], crustacea, who)

    classify_validate_all(ADMIN_AUTH)

    # Admin BAK-exports it
    req = dict(BAK_EXP_TMPL, **{"project_id": prj_id})
    req_and_filters = {"filters": {}, "request": req}
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    export_job_id = rsp.json()["job_id"]
    wait_for_stable(export_job_id)
    api_check_job_ok(fastapi, export_job_id)
    url = JOB_QUERY_URL.format(job_id=export_job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    file_in_ftp = job_dict["result"]["out_file"]

    do_import_update(
        prj_id,
        caplog,
        "Cla",
        str(DATA_DIR / "ftp" / ("task_%d_%s" % (export_job_id, file_in_ftp))),
    )
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # There should be no update, even if export of classif_when truncates microseconds
    assert nb_upds == 0

    # Re-classify different ID
    classify_validate_all(ADMIN_AUTH, True)
    # Oops, let's get back to saved state
    do_import_update(
        prj_id,
        caplog,
        "Cla",
        str(DATA_DIR / "ftp" / ("task_%d_%s" % (export_job_id, file_in_ftp))),
    )
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # All changed, restored to backup
    assert nb_upds == 15

    # Re-classify different user
    classify_validate_all(USER_AUTH, False)
    # Admin wants _his_ name back
    do_import_update(
        prj_id,
        caplog,
        "Cla",
        str(DATA_DIR / "ftp" / ("task_%d_%s" % (export_job_id, file_in_ftp))),
    )
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # All changed, restored to backup
    assert nb_upds == 15
