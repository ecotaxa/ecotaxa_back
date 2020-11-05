import logging

# noinspection PyPackageRequirements
from starlette import status

from tests.credentials import ADMIN_AUTH
from tests.test_collections import COLLECTION_CREATE_URL
from tests.test_fastapi import PROJECT_QUERY_URL

COLLECTION_EXPORT_EMODNET_URL = "/collections/{collection_id}/export/emodnet?dry_run=False"

TASK_DOWNLOAD_URL = "/tasks/{task_id}/file"


def test_emodnet_export(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "EMODNET project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "EMODNET project")

    # And grants ADMIN on the imported project to Real User
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    read_json = rsp.json()

    # Create a minimal collection with only this project
    url = COLLECTION_CREATE_URL
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"title": "Test collection",
                                                      "project_ids": [prj_id]})
    assert rsp.status_code == status.HTTP_200_OK
    coll_id = rsp.json()

    # Export the collection
    #     url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    #     minimal_real_user = {"id": REAL_USER_ID, "email": "unused", "name": "unused"}
    #     read_json["managers"] = [minimal_real_user]
    #     # read_json["owner"] = minimal_real_user
    #     read_json["comments"] = """ This series is part of the long term planktonic monitoring of
    # Villefranche-sur-mer, which is one of the oldest and richest in the world.
    # The data collection and processing has been funded by several projects
    # over its lifetime. It is currently supported directly by the Institut de la Mer
    # de Villefranche (IMEV), as part of its long term monitoring effort. """
    #     read_json["license"] = "CC BY 4.0"
    #     rsp = fastapi.put(url, headers=ADMIN_AUTH, json=read_json)
    #     assert rsp.status_code == status.HTTP_200_OK

    caplog.set_level(logging.DEBUG)
    # Admin exports it
    # req = EMODnetExportReq(project_ids=[prj_id])
    url = COLLECTION_EXPORT_EMODNET_URL.format(collection_id=coll_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["errors"] == ["Collection 'abstract' field is empty",
                                    "Collection license should be one of [<LicenseEnum.CC0: 'CC0 1.0'>, "
                                    "<LicenseEnum.CC_BY: 'CC BY 4.0'>, <LicenseEnum.CC_BY_NC: 'CC BY-NC 4.0'>] to be "
                                    "accepted, not Copyright."]
    assert rsp.json()["warnings"] == ['Classification detritus (with id 84963) could not be matched in WoRMS',
                                      'Classification other (with id 85011) could not be matched in WoRMS',
                                      'Classification t001 (with id 85012) could not be matched in WoRMS',
                                      'Classification egg (with id 85078) could not be matched in WoRMS']

    task_id = rsp.json()["task_id"]
    assert task_id == 0  # No valid task as there were errors

    # # Download the result zip
    # url = TASK_DOWNLOAD_URL.format(task_id=task_id)
    # # Ensure it's not public
    # rsp = fastapi.get(url)
    # assert rsp.status_code == status.HTTP_403_FORBIDDEN
    # # But the creator can get it
    # rsp = fastapi.get(url, headers=REAL_USER_AUTH)
    # assert rsp.status_code == status.HTTP_200_OK
    # Admin can get it
    # rsp = fastapi.get(url, headers=ADMIN_AUTH)
    # assert rsp.status_code == status.HTTP_200_OK
