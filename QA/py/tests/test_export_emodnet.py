import datetime
import logging

# noinspection PyPackageRequirements
from io import BytesIO
from unittest import mock
from zipfile import ZipFile

from starlette import status

from tests.credentials import ADMIN_AUTH, REAL_USER_ID, CREATOR_AUTH, ADMIN_USER_ID
from tests.emodnet_ref import (
    ref_zip,
    with_absent_zip,
    no_computations_zip,
    no_predicted_zip,
)
from tests.export_shared import JOB_DOWNLOAD_URL
from tests.formulae import uvp_formulae
from tests.test_classification import _prj_query, OBJECT_SET_CLASSIFY_URL
from tests.test_collections import (
    COLLECTION_CREATE_URL,
    COLLECTION_UPDATE_URL,
    COLLECTION_QUERY_URL,
)
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import PLAIN_FILE, MIX_OF_STATES
from tests.test_jobs import wait_for_stable, api_check_job_ok, api_check_job_failed
from tests.test_update import ACQUISITION_SET_UPDATE_URL, SAMPLE_SET_UPDATE_URL
from tests.test_update_prj import PROJECT_UPDATE_URL

COLLECTION_EXPORT_EMODNET_URL = "/collections/export/darwin_core"

_req_tmpl = {
    "collection_id": None,
    "dry_run": False,
    "include_predicted": True,
    "with_absent": False,
    "with_computations": [],
    "formulae": uvp_formulae,
}

COLLECTION_QUERY_BY_TITLE_URL = "/collections/by_title/?q={title}"

PROJECT_SEARCH_SAMPLES_URL = "/api/samples/search?project_ids={project_id}&id_pattern="
PROJECT_SEARCH_ACQUIS_URL = "/acquisitions/search?project_id={project_id}"


def test_emodnet_export(config, database, fastapi, caplog):
    fixed_date = datetime.datetime(2021, 7, 10, 11, 22, 33)
    with mock.patch("helpers.DateTime._now_time", return_value=fixed_date):
        do_test_emodnet_export(config, database, fastapi, caplog)


def do_test_emodnet_export(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    coll_id, coll_title, prj_id, prj_json = create_test_collection(
        caplog, config, database, fastapi, "exp"
    )

    caplog.set_level(logging.DEBUG)

    # Admin exports it
    # First attempt with LOTS of missing data
    req = _req_tmpl.copy()
    req.update(
        {
            "collection_id": coll_id,
            "with_absent": True,
            "with_computations": ["ABO", "CNC", "BIV"],
        }
    )
    rsp = fastapi.post(COLLECTION_EXPORT_EMODNET_URL, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    rsp = api_check_job_failed(fastapi, job_id, "5 error(s) during run")
    json = rsp.json()
    assert json["errors"] == [
        "No valid data creator (user or organisation) found for EML metadata.",
        "No valid contact user found for EML metadata.",
        "No valid metadata provider user found for EML metadata.",
        "Collection 'abstract' field is empty",
        "Collection license should be one of [<LicenseEnum.CC0: 'CC0 1.0'>, "
        "<LicenseEnum.CC_BY: 'CC BY 4.0'>, <LicenseEnum.CC_BY_NC: 'CC BY-NC 4.0'>] to be "
        "accepted, not .",
    ]
    assert "warnings" not in json

    # Validate nearly everything, otherwise no export.
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 20
    # The first Actinopterygii object in m106_mn01_n3_sml remains Predicted and the second one is imported Validated
    actinopters = _prj_query(fastapi, CREATOR_AUTH, prj_id, taxo="92731")
    assert len(actinopters) == 2
    for an_objid in actinopters:  # No need to validate any of them
        obj_ids.remove(an_objid)
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

    # Update underlying project license
    url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    prj_json["license"] = "CC BY 4.0"
    # And give a contact who is now mandatory
    prj_json["contact"] = prj_json["managers"][0]
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=prj_json)
    assert rsp.status_code == status.HTTP_200_OK

    add_concentration_data(fastapi, prj_id)

    # Update the collection to fill in missing data
    url = COLLECTION_QUERY_URL.format(collection_id=coll_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    the_coll = rsp.json()
    url = COLLECTION_UPDATE_URL.format(collection_id=coll_id)
    the_coll[
        "abstract"
    ] = """
This series is part of the long term planktonic monitoring of
    # Villefranche-sur-mer, which is one of the oldest and richest in the world.
    # The data collection and processing has been funded by several projects
    # over its lifetime. It is currently supported directly by the Institut de la Mer
    # de Villefranche (IMEV), as part of its long term monitoring effort.
    """
    the_coll[
        "license"
    ] = "CC BY 4.0"  # Would do nothing as the license comes from the underlying project
    user_doing_all = {
        "id": REAL_USER_ID,
        # TODO: below is redundant with ID and ignored, but fails validation (http 422) if not set
        "email": "creator",
        "name": "User Creating Projects",
    }
    the_coll["creator_users"] = [user_doing_all]
    the_coll["contact_user"] = user_doing_all
    the_coll["provider_user"] = user_doing_all
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=the_coll)
    assert rsp.status_code == status.HTTP_200_OK

    req = _req_tmpl.copy()
    req.update({"collection_id": coll_id, "with_computations": ["ABO", "CNC", "BIV"]})
    rsp = fastapi.post(COLLECTION_EXPORT_EMODNET_URL, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    job_status = api_check_job_ok(fastapi, job_id)
    warns = job_status["result"]["wrns"]
    ref_warns = [
        "Could not extract sampling net name and features from sample m106_mn01_n1_sml (at least one of ['net_type', 'net_mesh', 'net_surf'] free column is absent).",
        "Could not extract sampling net name and features from sample m106_mn01_n2_sml (at least one of ['net_type', 'net_mesh', 'net_surf'] free column is absent).",
        "No occurrence added for sample 'm106_mn01_n2_sml' in project #%d" % prj_id,
        "Could not extract sampling net name and features from sample m106_mn01_n3_sml (at least one of ['net_type', 'net_mesh', 'net_surf'] free column is absent).",
        "Could not extract sampling net name and features from sample m106_mn04_n4_sml (at least one of ['net_type', 'net_mesh', 'net_surf'] free column is absent).",
        "Sample 'm106_mn04_n4_sml' taxo(s) #[1, 78418]: Computed concentration is NaN, input data is missing or incorrect",
        "Sample 'm106_mn04_n4_sml' taxo(s) #[1, 78418]: Computed biovolume is NaN, input data is missing or incorrect",
        "Could not extract sampling net name and features from sample m106_mn04_n5_sml (at least one of ['net_type', 'net_mesh', 'net_surf'] free column is absent).",
        "Some values could not be converted to float in {'sql_count': 1, 'sam_tot_vol': 'foo', 'ssm_sub_part': '8'}",
        "Some values could not be converted to float in {'sql_count': 1, 'sam_tot_vol': 'foo', 'ssm_sub_part': '8'}",
        "Sample 'm106_mn04_n5_sml' taxo(s) #[1, 78418]: Computed concentration is NaN, input data is missing or incorrect",
        "Some values could not be converted to float in {'obj_area': 1511.0, 'sam_tot_vol': 'foo', 'ssm_pixel': '10.6', 'ssm_sub_part': '8'}",
        "Some values could not be converted to float in {'obj_area': 1583.0, 'sam_tot_vol': 'foo', 'ssm_pixel': '10.6', 'ssm_sub_part': '8'}",
        "Sample 'm106_mn04_n5_sml' taxo(s) #[1, 78418]: Computed biovolume is NaN, input data is missing or incorrect",
        "Could not extract sampling net name and features from sample m106_mn04_n6_sml (at least one of ['net_type', 'net_mesh', 'net_surf'] free column is absent).",
        "Some values could not be converted to float in {'sql_count': 1, 'sam_tot_vol': '2000', 'ssm_sub_part': 'hi'}",
        "Some values could not be converted to float in {'sql_count': 1, 'sam_tot_vol': '2000', 'ssm_sub_part': 'hi'}",
        "Some values could not be converted to float in {'sql_count': 1, 'sam_tot_vol': '2000', 'ssm_sub_part': 'hi'}",
        "Sample 'm106_mn04_n6_sml' taxo(s) #[1, 45072, 78418]: Computed concentration is NaN, input data is missing or incorrect",
        "Some values could not be converted to float in {'obj_area': 1583.0, 'sam_tot_vol': '2000', 'ssm_pixel': '10.6', 'ssm_sub_part': 'hi'}",
        "Some values could not be converted to float in {'obj_area': 1583.0, 'sam_tot_vol': '2000', 'ssm_pixel': '10.6', 'ssm_sub_part': 'hi'}",
        "Some values could not be converted to float in {'obj_area': 1583.0, 'sam_tot_vol': '2000', 'ssm_pixel': '10.6', 'ssm_sub_part': 'hi'}",
        "Sample 'm106_mn04_n6_sml' taxo(s) #[1, 45072, 78418]: Computed biovolume is NaN, input data is missing or incorrect",
        "Stats: predicted:1 validated:19 produced to zip:9 not produced (M):11 not produced (P):0",
    ]
    assert warns == ref_warns
    assert rsp.json()["errors"] == []
    # job_id = rsp.json()["job_id"]

    # Download the result zip
    url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    # Ensure it's not public
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    # But the creator can get it
    # rsp = fastapi.get(url, headers=REAL_USER_AUTH)
    # assert rsp.status_code == status.HTTP_200_OK

    # Admin can get it
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    unzip_and_check(rsp.content, ref_zip)

    req = _req_tmpl.copy()
    req.update(
        {
            "collection_id": coll_id,
            "with_absent": True,
            "with_computations": ["ABO", "CNC", "BIV"],
        }
    )
    rsp = fastapi.post(COLLECTION_EXPORT_EMODNET_URL, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, with_absent_zip)

    req = _req_tmpl.copy()
    req.update({"collection_id": coll_id})
    rsp = fastapi.post(COLLECTION_EXPORT_EMODNET_URL, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, no_computations_zip)

    # Foreseen options for June 2023-like exports
    req = _req_tmpl.copy()
    req.update(
        {
            "collection_id": coll_id,
            "include_predicted": False,
            "with_computations": ["ABO", "CNC", "BIV"],
            "pre_mapping": {
                45072: 56693,  # Cyclopoida -> Actinopterygii
                78418: None,  # Oncaeidae -> remove
            },
        }
    )
    rsp = fastapi.post(COLLECTION_EXPORT_EMODNET_URL, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, no_predicted_zip)

    url_query_back = COLLECTION_QUERY_BY_TITLE_URL.format(title=coll_title)
    rsp = fastapi.get(url_query_back)
    assert rsp.status_code == status.HTTP_200_OK
    coll_desc = rsp.json()
    assert coll_desc["title"] == coll_title


def create_test_collection(caplog, config, database, fastapi, suffix):
    # In these TSVs, we have: object_major, object_minor, object_area, process_pixel
    # Admin imports the project
    from tests.test_import import (
        BAD_FREE_DIR,
        test_import,
        do_import,
        test_import_a_bit_more_skipping,
    )

    project = "EMODNET project " + suffix
    prj_id = test_import(config, database, caplog, project, str(PLAIN_FILE), "UVP6")
    # Add a sample spanning 2 days (m106_mn01_n3_sml) for testing date ranges in event.txt
    # this sample contains 2 'detritus' at load time and 1 small<egg (92731) which resolves to nearest Phylo Actinopterygii (56693)
    test_import_a_bit_more_skipping(config, database, caplog, project)
    # Add a similar but predicted object into same sample m106_mn01_n3_sml
    test_import_a_bit_more_skipping(
        config, database, caplog, project, str(MIX_OF_STATES)
    )
    # Add a sample with corrupted or absent needed free columns, for provoking calculation warnings
    do_import(prj_id, BAD_FREE_DIR, ADMIN_USER_ID)
    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    coll_title = "EMODNET test collection " + suffix
    # Create a minimal collection with only this project
    url = COLLECTION_CREATE_URL
    rsp = fastapi.post(
        url, headers=ADMIN_AUTH, json={"title": coll_title, "project_ids": [prj_id]}
    )
    assert rsp.status_code == status.HTTP_200_OK
    coll_id = rsp.json()
    return coll_id, coll_title, prj_id, prj_json


def test_emodnet_endpoint(config, database, fastapi, caplog):
    req = _req_tmpl.copy()
    req.update(
        {
            "collection_id": 0,
            "pre_mapping": {  # Loop in mapping, not allowed
                45072: 78418,
                78418: 45072,
            },
        }
    )
    rsp = fastapi.post(COLLECTION_EXPORT_EMODNET_URL, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "inconsistent" in str(rsp.content)


def unzip_and_check(zip_content, ref_content):
    pseudo_file = BytesIO(zip_content)
    zip = ZipFile(pseudo_file)
    all_in_one = {}
    for a_file in zip.filelist:
        name = a_file.filename
        with zip.open(name) as myfile:
            content_bin = myfile.read()
            file_content = content_bin.decode("utf-8")
            print(file_content)
            print()
            # Add CRs before and after for readability of the py version
            all_in_one[name] = "\n" + file_content + "\n"
    assert all_in_one == ref_content


def add_concentration_data(fastapi, prj_id):
    # Update Acquisitions & Samples so that there can be a concentration,
    # only some of them so that on-purpose erroneous data survives
    url = PROJECT_SEARCH_SAMPLES_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    sample_ids = [r["sampleid"] for r in rsp.json() if "mn04" not in r["orig_id"]]
    url = SAMPLE_SET_UPDATE_URL.format(project_id=prj_id)
    req = {"target_ids": sample_ids, "updates": [{"ucol": "tot_vol", "uval": "100"}]}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == len(sample_ids)
    url = PROJECT_SEARCH_ACQUIS_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    acquis_ids = [r["acquisid"] for r in rsp.json() if "mn04" not in r["orig_id"]]
    url = ACQUISITION_SET_UPDATE_URL.format(project_id=prj_id)
    req = {"target_ids": acquis_ids, "updates": [{"ucol": "sub_part", "uval": "2"}]}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == len(acquis_ids)


def test_names():
    from API_operations.exports.DarwinCore import DarwinCoreExport

    assert DarwinCoreExport.capitalize_name("JEAN") == "Jean"
    assert DarwinCoreExport.capitalize_name("JEAN-MARC") == "Jean-Marc"
    assert DarwinCoreExport.capitalize_name("FOo--BAR") == "Foo--Bar"
    assert DarwinCoreExport.capitalize_name("FOo-- 1 BAR") == "Foo-- 1 Bar"
