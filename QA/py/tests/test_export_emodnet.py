import logging

# noinspection PyPackageRequirements
from starlette import status

from API_operations.exports.EMODnet import EMODnetExport

from tests.credentials import ADMIN_AUTH, CREATOR_USER_ID, REAL_USER_ID
from tests.test_collections import COLLECTION_CREATE_URL, COLLECTION_UPDATE_URL, COLLECTION_QUERY_URL
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_update import ACQUISITION_SET_UPDATE_URL, SAMPLE_SET_UPDATE_URL
from tests.test_update_prj import PROJECT_UPDATE_URL

COLLECTION_EXPORT_EMODNET_URL = "/collections/{collection_id}/export/emodnet?dry_run=False"

TASK_DOWNLOAD_URL = "/tasks/{task_id}/file"

PROJECT_SEARCH_SAMPLES_URL = "/samples/search?project_id={project_id}"
PROJECT_SEARCH_ACQUIS_URL = "/acquisitions/search?project_id={project_id}"


def test_emodnet_export(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "EMODNET project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "EMODNET project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    prj_json = rsp.json()

    # Create a minimal collection with only this project
    url = COLLECTION_CREATE_URL
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"title": "EMODNET test collection",
                                                      "project_ids": [prj_id]})
    assert rsp.status_code == status.HTTP_200_OK
    coll_id = rsp.json()

    caplog.set_level(logging.DEBUG)

    # Admin exports it
    # First attempt with LOTS of missing data
    url = COLLECTION_EXPORT_EMODNET_URL.format(collection_id=coll_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["errors"] == ['No valid data creator (user or organisation) found for EML metadata.',
                                    'No valid contact user found for EML metadata.',
                                    "No valid metadata provider user found for EML metadata.",
                                    "Collection 'abstract' field is empty",
                                    "Collection license should be one of [<LicenseEnum.CC0: 'CC0 1.0'>, "
                                    "<LicenseEnum.CC_BY: 'CC BY 4.0'>, <LicenseEnum.CC_BY_NC: 'CC BY-NC 4.0'>] to be "
                                    "accepted, not ."]
    assert rsp.json()["warnings"] == []
    task_id = rsp.json()["task_id"]
    assert task_id == 0  # No valid task as there were errors

    # Update underlying project license
    url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    prj_json["license"] = "CC BY 4.0"
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
                      # TODO: below is redundant with ID, ignored, but fails validation (http 422) if not set
                      'email': 'creator',
                      'name': 'User Creating Projects'
                      }
    the_coll['creator_users'] = [user_doing_all]
    the_coll['contact_user'] = user_doing_all
    the_coll['provider_user'] = user_doing_all
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=the_coll)
    assert rsp.status_code == status.HTTP_200_OK

    url = COLLECTION_EXPORT_EMODNET_URL.format(collection_id=coll_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    warns = rsp.json()["warnings"]
    #assert warns == []
    assert rsp.json()["errors"] == []
    task_id = rsp.json()["task_id"]

    # Download the result zip
    url = TASK_DOWNLOAD_URL.format(task_id=task_id)
    # Ensure it's not public
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    # But the creator can get it
    # rsp = fastapi.get(url, headers=REAL_USER_AUTH)
    # assert rsp.status_code == status.HTTP_200_OK
    # Admin can get it
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK


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
               [{"ucol": "sub_part", "uval": "0.5"}]
           }
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == len(acquis_ids)


def test_names():
    assert EMODnetExport.capitalize_name("JEAN") == "Jean"
    assert EMODnetExport.capitalize_name("JEAN-MARC") == "Jean-Marc"
    assert EMODnetExport.capitalize_name("FOo--BAR") == "Foo--Bar"
    assert EMODnetExport.capitalize_name("FOo-- 1 BAR") == "Foo-- 1 Bar"
