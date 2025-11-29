import logging
from typing import Dict, List

from starlette import status

from tests.credentials import CREATOR_AUTH, ADMIN_AUTH, ADMIN_USER_ID
from tests.export_shared import download_and_check
from tests.formulae import uvp_formulae
from tests.jobs import get_job_and_wait_until_ok
from tests.test_classification import OBJECT_SET_CLASSIFY_URL
from tests.test_export_emodnet import add_concentration_data, PROJECT_SEARCH_SAMPLES_URL
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import DATA_DIR, do_import
from tests.test_objectset_query import _prj_query
from tests.test_update_prj import PROJECT_UPDATE_URL

OBJECT_SET_SUMMARY_EXPORT_URL = "/object_set/export/summary"


def set_formulae_in_project(fastapi, prj_id: int, prj_formulae: Dict):
    from tests.test_project_vars import BODC_VARS_KEY

    read_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(read_url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    prj_json = rsp.json()
    prj_json[BODC_VARS_KEY] = prj_formulae
    upd_url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(upd_url, headers=ADMIN_AUTH, json=prj_json)
    assert rsp.status_code == status.HTTP_200_OK


def test_export_abundances(database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project, which is an export expected result
    from tests.test_import import test_import

    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id = test_import(database, caplog, "TSV sci export", path=path)
    set_formulae_in_project(
        fastapi, prj_id, uvp_formulae
    )  # Note: This is _not_ needed for abundances

    # Validate all, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
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

    # Abundance export whole project
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "summarise_by": "none"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_whole_project", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by sample, default values everywhere
    req_and_filters = {"filters": {}, "request": {"project_id": prj_id}}
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by subsample
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "summarise_by": "acquisition"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_subsample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by subsample but playing with taxa mapping
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "summarise_by": "acquisition",
            "taxo_mapping": {
                85012: None,  # t001 -> Remove
                84963: None,  # detritus -> Remove
                85078: 78418,  # egg<other -> Oncaeidae
                92731: 78418,  # small<egg -> Oncaeidae
            },
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_subsample_mapped", only_hdr=True)
    # log = get_log_file(fastapi, job_id)


def test_export_conc_biovol(database, fastapi, caplog):
    """Specific test for concentrations and biovolume"""
    # Admin imports the project
    from tests.test_import import (
        test_import,
        test_import_a_bit_more_skipping,
        WEIRD_DIR,
    )

    prj_id = test_import(database, caplog, "SCISUM project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(database, caplog, "SCISUM project")
    # Store computation variables
    set_formulae_in_project(fastapi, prj_id, uvp_formulae)
    # Add some data for calculations
    add_concentration_data(fastapi, prj_id)
    # Add a sample with weird data in free columns:
    # rightmost column acq_sub_part in TSV has unusual values
    # date format is mixed
    do_import(prj_id, WEIRD_DIR, ADMIN_USER_ID)
    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    # Validate everything, otherwise no export.
    obj_ids: List[int] = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 15
    url = OBJECT_SET_CLASSIFY_URL
    obj_ids.sort()
    just_some_objs = obj_ids[::2]  # 1,3,5,...19
    classifications = [-1 for _obj in just_some_objs]  # Keep current
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": just_some_objs,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    # Concentrations export by sample
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "quantity": "concentration"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "concentrations_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Biovolume export by sample
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "quantity": "biovolume"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Biovolume export by subsample AKA Acquisition
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "quantity": "biovolume",
            "summarise_by": "acquisition",
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_subsample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Biovolume export by subsample AKA Acquisition, only validated ones.
    # biovols are identical to un-filtered ones
    req_and_filters = {
        "filters": {"statusfilter": "V"},
        "request": {
            "project_id": prj_id,
            "quantity": "biovolume",
            "summarise_by": "acquisition",
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_subsample_only_v", only_hdr=True)
    # log = get_log_file(fastapi, job_id)


def test_export_abundances_filtered_by_taxo(database, fastapi, caplog):
    """Simulate calls to export with an active filter"""
    caplog.set_level(logging.FATAL)

    # TODO: Dup code for the data load
    # Admin imports the project, which is an export expected result
    from tests.test_import import test_import

    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id = test_import(database, caplog, "TSV sci export filtered", path=path)
    set_formulae_in_project(fastapi, prj_id, uvp_formulae)  # Not needed

    # Validate all, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
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

    # Abundance export, per sample with a filter on a category
    req_and_filters = {
        "filters": {
            "taxo": "45072",
            "taxochild": "Y",
        },  # TODO: Not very useful as the test has a very reduced tree
        "request": {"project_id": prj_id},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(
        fastapi, job_id, "abundances_by_sample_filtered_on_cat", only_hdr=True
    )


def test_export_abundances_filtered_by_sample(database, fastapi, caplog):
    """Simulate calls to export with an active filter"""
    caplog.set_level(logging.FATAL)

    # TODO: Dup code for the data load
    # Admin imports the project, which is an export expected result
    from tests.test_import import test_import

    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id = test_import(database, caplog, "TSV sci export filtered", path=path)
    set_formulae_in_project(fastapi, prj_id, uvp_formulae)

    # Validate all, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
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

    # Abundance export, per sample with a filter on samples
    url = PROJECT_SEARCH_SAMPLES_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    # TODO: This need for IDs in the API is a bit of pain
    sample_ids = [str(r["sampleid"]) for r in rsp.json() if "n2" not in r["orig_id"]]

    req_and_filters = {
        "filters": {"samples": ",".join(sample_ids)},
        "request": {"project_id": prj_id},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(
        fastapi, job_id, "abundances_by_sample_filtered_on_sample", only_hdr=True
    )
