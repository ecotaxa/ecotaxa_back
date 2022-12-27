import datetime
import logging
# noinspection PyPackageRequirements
from io import BytesIO
from zipfile import ZipFile

from starlette import status
from unittest import mock

from tests.credentials import ADMIN_AUTH, REAL_USER_ID, CREATOR_AUTH
from tests.emodnet_ref import ref_zip, with_zeroes_zip, no_computations_zip
from tests.export_shared import JOB_DOWNLOAD_URL
from tests.test_classification import _prj_query, OBJECT_SET_CLASSIFY_URL
from tests.test_collections import COLLECTION_CREATE_URL, COLLECTION_UPDATE_URL, COLLECTION_QUERY_URL
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_jobs import wait_for_stable, api_check_job_ok, api_check_job_failed
from tests.test_update import ACQUISITION_SET_UPDATE_URL, SAMPLE_SET_UPDATE_URL
from tests.test_update_prj import PROJECT_UPDATE_URL

COLLECTION_EXPORT_EMODNET_URL = "/collections/{collection_id}/export/darwin_core?dry_run={dry}" \
                                "&with_zeroes={zeroes}&with_computations={comp}&auto_morpho={morph}"

COLLECTION_QUERY_BY_TITLE_URL = "/collections/by_title/?q={title}"

PROJECT_SEARCH_SAMPLES_URL = "/api/samples/search?project_ids={project_id}&id_pattern="
PROJECT_SEARCH_ACQUIS_URL = "/acquisitions/search?project_id={project_id}"


def test_emodnet_export(config, database, fastapi, caplog):
    fixed_date = datetime.datetime(2021, 7, 10, 11, 22, 33)
    with mock.patch('helpers.DateTime._now_time',
                    return_value=fixed_date):
        do_test_emodnet_export(config, database, fastapi, caplog)


def do_test_emodnet_export(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # TODO TODO TODO: The data does _not_ allow to generate biovolume

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "EMODNET project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "EMODNET project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    prj_json = rsp.json()

    coll_title = "EMODNET test collection"
    # Create a minimal collection with only this project
    url = COLLECTION_CREATE_URL
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"title": coll_title,
                                                      "project_ids": [prj_id]})
    assert rsp.status_code == status.HTTP_200_OK
    coll_id = rsp.json()

    caplog.set_level(logging.DEBUG)

    # Admin exports it
    # First attempt with LOTS of missing data
    url = COLLECTION_EXPORT_EMODNET_URL.format(collection_id=coll_id, dry=False, zeroes=True, comp=True, morph=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = wait_for_stable(job_id)
    api_check_job_failed(fastapi, job_id, '5 error(s) during run')
    # TODO: Errors text
    # assert rsp.json()["errors"] == ['No valid data creator (user or organisation) found for EML metadata.',
    #                                 'No valid contact user found for EML metadata.',
    #                                 "No valid metadata provider user found for EML metadata.",
    #                                 "Collection 'abstract' field is empty",
    #                                 "Collection license should be one of [<LicenseEnum.CC0: 'CC0 1.0'>, "
    #                                 "<LicenseEnum.CC_BY: 'CC BY 4.0'>, <LicenseEnum.CC_BY_NC: 'CC BY-NC 4.0'>] to be "
    #                                 "accepted, not ."]
    # assert rsp.json()["warnings"] == []

    # Validate everything, otherwise no export.
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 11
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]  # Keep current
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"target_ids": obj_ids,
                                                      "classifications": classifications,
                                                      "wanted_qualification": "V"})
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
    the_coll['abstract'] = """
This series is part of the long term planktonic monitoring of
    # Villefranche-sur-mer, which is one of the oldest and richest in the world.
    # The data collection and processing has been funded by several projects
    # over its lifetime. It is currently supported directly by the Institut de la Mer
    # de Villefranche (IMEV), as part of its long term monitoring effort.
    """
    the_coll['license'] = "CC BY 4.0"  # Would do nothing as the license comes from the underlying project
    user_doing_all = {'id': REAL_USER_ID,
                      # TODO: below is redundant with ID and ignored, but fails validation (http 422) if not set
                      'email': 'creator',
                      'name': 'User Creating Projects'
                      }
    the_coll['creator_users'] = [user_doing_all]
    the_coll['contact_user'] = user_doing_all
    the_coll['provider_user'] = user_doing_all
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=the_coll)
    assert rsp.status_code == status.HTTP_200_OK

    url = COLLECTION_EXPORT_EMODNET_URL.format(collection_id=coll_id, dry=False, zeroes=False, comp=True, morph=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    # warns = rsp.json()["warnings"]
    # # assert warns == []
    # assert rsp.json()["errors"] == []
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

    url_with_0s = COLLECTION_EXPORT_EMODNET_URL.format(collection_id=coll_id, dry=False, zeroes=True, comp=True,
                                                       morph=False)
    rsp = fastapi.get(url_with_0s, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, with_zeroes_zip)

    url_raw_data = COLLECTION_EXPORT_EMODNET_URL.format(collection_id=coll_id, dry=False, zeroes=False, comp=False,
                                                        morph=False)
    rsp = fastapi.get(url_raw_data, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, no_computations_zip)

    url_query_back = COLLECTION_QUERY_BY_TITLE_URL.format(title=coll_title)
    rsp = fastapi.get(url_query_back)
    assert rsp.status_code == status.HTTP_200_OK
    coll_desc = rsp.json()
    assert coll_desc['title'] == coll_title


def unzip_and_check(zip_content, ref_content):
    pseudo_file = BytesIO(zip_content)
    zip = ZipFile(pseudo_file)
    all_in_one = {}
    for a_file in zip.filelist:
        name = a_file.filename
        with zip.open(name) as myfile:
            content_bin = myfile.read()
            file_content = content_bin.decode('utf-8')
            print(file_content)
            print()
            # Add CRs before and after for readability of the py version
            all_in_one[name] = "\n" + file_content + "\n"
    assert all_in_one == ref_content


def add_concentration_data(fastapi, prj_id):
    # Update Acquisitions & Samples so that there can be a concentration
    url = PROJECT_SEARCH_SAMPLES_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    sample_ids = [r["sampleid"] for r in rsp.json()]
    url = SAMPLE_SET_UPDATE_URL.format(project_id=prj_id)
    req = {"target_ids": sample_ids,
           "updates":
               [{"ucol": "tot_vol", "uval": "100"}]
           }
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == len(sample_ids)
    url = PROJECT_SEARCH_ACQUIS_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    acquis_ids = [r["acquisid"] for r in rsp.json()]
    url = ACQUISITION_SET_UPDATE_URL.format(project_id=prj_id)
    req = {"target_ids": acquis_ids,
           "updates":
               [{"ucol": "sub_part", "uval": "2"}]
           }
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == len(acquis_ids)


def test_names():
    from API_operations.exports.DarwinCore import DarwinCoreExport
    assert DarwinCoreExport.capitalize_name("JEAN") == "Jean"
    assert DarwinCoreExport.capitalize_name("JEAN-MARC") == "Jean-Marc"
    assert DarwinCoreExport.capitalize_name("FOo--BAR") == "Foo--Bar"
    assert DarwinCoreExport.capitalize_name("FOo-- 1 BAR") == "Foo-- 1 Bar"
