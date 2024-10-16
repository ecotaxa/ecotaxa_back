import datetime
import json
import logging
from typing import Dict, Any
from unittest import mock

import pytest
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
    crustacea_id,
    classif_history,
)
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import create_project, do_import, DATA_DIR, dump_project
from tests.test_import_update import do_import_update
from tests.test_subentities import current_object
from tests.test_update_prj import PROJECT_UPDATE_URL

DEPRECATED_OBJECT_SET_EXPORT_URL = "/object_set/export"

DEPRECATED_GEN_EXPORT_TMPL = {
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

DEPRECATED_BAK_EXP_TMPL = {
    "exp_type": "BAK",
    "tsv_entities": "",  # Defaulted by type
    "coma_as_separator": True,  # Defaulted by type
    "format_dates_times": True,  # Defaulted by type
    "with_images": True,
    "only_first_image": True,  # Defaulted by type
    "split_by": "",  # Defaulted by type
    "with_internal_ids": True,  # Defaulted by type
    "out_to_ftp": True,
    "sum_subtotal": "",  # Defaulted by type
}

OBJECT_SET_GENERAL_EXPORT_URL = "/object_set/export/general"
OBJECT_SET_BACKUP_EXPORT_URL = "/object_set/export/backup"


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
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "split_by": "sample"},
    }
    rsp = fastapi.post(
        OBJECT_SET_GENERAL_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "tsv_all_entities_no_img_no_ids")

    # Backup export
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_BACKUP_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_all_images")

    # TSV export with IDs
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "split_by": "sample",
            "with_internal_ids": True,
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_GENERAL_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # Too much randomness inside: IDs, random value
    # TODO: Better comparison ignoring columns
    # TODO: Decide if we should emulate now missing auto_ fields
    # download_and_unzip_and_check(fastapi, job_id, "tsv_with_ids", only_hdr=True)

    # TSV export by acquisition
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "split_by": "acquisition",
            "with_images": "all",
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_GENERAL_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "tsv_by_acquisition")

    # TSV export by taxon
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "split_by": "taxon",
            "with_images": "first",  # Avoid dups in TSV
            "with_types_row": True,
            "out_to_ftp": True,
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_GENERAL_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "tsv_by_taxon")


def test_deprecated_export_tsv(database, fastapi, caplog):
    """Still in /object_set/export for eventual unknown users"""
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping

    prj_id = test_import(database, caplog, "TSV deprecated export project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(database, caplog, "TSV deprecated export project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    _prj_json = rsp.json()

    caplog.set_level(logging.DEBUG)

    # Backup export without images (but their ref is still in the TSVs)
    # Deprecated (Jan 2024), backup means produce all the data needed to restore all
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "exp_type": "BAK",
        },
    }
    rsp = fastapi.post(
        DEPRECATED_OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_no_image")

    # DOI export
    # Deprecated (Jan 2024)
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "exp_type": "DOI",
        },
    }
    fixed_date = datetime.datetime(2021, 5, 30, 11, 22, 33)
    with mock.patch("helpers.DateTime._now_time", return_value=fixed_date):
        rsp = fastapi.post(
            DEPRECATED_OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
        )
        assert rsp.status_code == status.HTTP_200_OK
        _job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # The object_id inside prevents predictability
    # TODO: Better comparison ignoring columns, inject project id and so on
    # download_and_unzip_and_check(fastapi, job_id, "doi", only_hdr=True)

    # Summary export, 3 types
    # Deprecated (Jan 2024)
    req_and_filters["request"].update(
        {"exp_type": "SUM", "out_to_ftp": True, "sum_subtotal": "S"}
    )
    rsp = fastapi.post(
        DEPRECATED_OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_sample", only_hdr=True)

    req_and_filters["request"].update(
        {"exp_type": "SUM", "out_to_ftp": True, "sum_subtotal": "A"}
    )
    rsp = fastapi.post(
        DEPRECATED_OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_subsample", only_hdr=True)

    req_and_filters["request"].update(
        {"exp_type": "SUM", "out_to_ftp": True, "sum_subtotal": ""}
    )
    rsp = fastapi.post(
        DEPRECATED_OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
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
    job_id, file_in_ftp = export_project_to_ftp(fastapi, prj_id, just_annots=False)

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


@pytest.mark.parametrize(
    "export_method", ["full", "annots"]
)  # Try two methods of saving annotation data
def test_export_roundtrip_self(database, fastapi, caplog, export_method):
    """Roundtrip export/validates/import self
    Scenario: Someone saves a validated project's classifs and wants to restore it to saved state.
    The format makes it possible to import update into another project, provided object_ids are present.
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
        classify_all(fastapi, obj_ids[1 if switch else 0 :: 2], crustacea_id, who)

    classify_validate_all(ADMIN_AUTH)

    # Admin BAK-exports it
    export_job_id, file_in_ftp = export_project_to_ftp(
        fastapi, prj_id, just_annots=export_method != "full"
    )

    do_import_update(
        prj_id,
        caplog,
        "Cla",
        str(DATA_DIR / "ftp" / ("task_%d_%s" % (export_job_id, file_in_ftp))),
    )
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # There should be no update, even if export of classif_when truncates microseconds
    assert nb_upds == 0

    # Re-classify with a different ID (idea...)
    classify_validate_all(ADMIN_AUTH, True)
    # And save the new classification, just annotations
    export_job_id2, file_in_ftp2 = export_project_to_ftp(
        fastapi, prj_id, just_annots=True
    )
    download_and_unzip_and_check(
        fastapi,
        export_job_id2,
        "just_annotations",
        only_hdr=True,  # We have just classified data inside TODO: Fix PG time somehow
        file_map={"ref.tsv": "ecotaxa_" + file_in_ftp2.replace(".zip", ".tsv")},
    )

    # Oops, let's get back to saved state
    do_import_update(
        prj_id,
        caplog,
        "Cla",
        str(DATA_DIR / "ftp" / ("task_%d_%s" % (export_job_id, file_in_ftp))),
    )
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # All changed, restored to backup state
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
    # All changed, restored to backup state
    assert nb_upds == 15

    if False:
        for an_obj in sorted(obj_ids):
            curr_obj = current_object(fastapi, an_obj)
            info = {k: v for k, v in curr_obj.items() if k.startswith("classif")}
            print(info)
            an_hist = classif_history(fastapi, an_obj)
            for hist in sorted(
                an_hist,
                key=lambda x: datetime.datetime.fromisoformat(x["classif_date"]),
                reverse=True,
            ):
                print(hist)
            print()

    for an_obj in obj_ids:
        an_hist = classif_history(fastapi, an_obj)
        assert len(an_hist) == 4

    # Restore a second time the same first backup
    do_import_update(
        prj_id,
        caplog,
        "Cla",
        str(DATA_DIR / "ftp" / ("task_%d_%s" % (export_job_id, file_in_ftp))),
    )
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # No change
    assert nb_upds == 0
    # Not more history
    for an_obj in obj_ids:
        an_hist = classif_history(fastapi, an_obj)
        assert len(an_hist) == 4

    # Restore the second backup, i.e. back in time
    do_import_update(
        prj_id,
        caplog,
        "Cla",
        str(DATA_DIR / "ftp" / ("task_%d_%s" % (export_job_id2, file_in_ftp2))),
    )
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # All changed
    assert nb_upds == 15
    # Not more history as all was historized before
    for an_obj in obj_ids:
        an_hist = classif_history(fastapi, an_obj)
        assert len(an_hist) == 4


def export_project_to_ftp(fastapi, prj_id, just_annots):
    req_and_filters = {  # Common param to both entry points
        "filters": {},
        "request": {
            "project_id": prj_id,
            "out_to_ftp": True,
        },
    }
    if just_annots:
        req_and_filters["request"]["only_annotations"] = True
    rsp = fastapi.post(
        OBJECT_SET_GENERAL_EXPORT_URL if just_annots else OBJECT_SET_BACKUP_EXPORT_URL,
        headers=ADMIN_AUTH,
        json=req_and_filters,
    )
    assert rsp.status_code == status.HTTP_200_OK
    export_job_id = rsp.json()["job_id"]
    wait_for_stable(export_job_id)
    api_check_job_ok(fastapi, export_job_id)
    url = JOB_QUERY_URL.format(job_id=export_job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    file_in_ftp = job_dict["result"]["out_file"]
    return export_job_id, file_in_ftp
