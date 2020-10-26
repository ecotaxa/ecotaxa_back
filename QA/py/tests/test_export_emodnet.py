import logging

from API_models.exports import *
# noinspection PyPackageRequirements
from API_operations.exports.EMODnet import EMODnetExport
from starlette import status

from tests.credentials import REAL_USER_ID, ADMIN_AUTH
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_update_prj import PROJECT_UPDATE_URL


def test_emodnet_export(config, database, fastapi, caplog):
    caplog.set_level(logging.DEBUG)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "EMODNET project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "EMODNET project")

    # And grants ADMIN on the imported project to Real User
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    read_json = rsp.json()

    url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    minimal_real_user = {"id": REAL_USER_ID, "email": "unused", "name": "unused"}
    read_json["managers"] = [minimal_real_user]
    read_json["owner"] = minimal_real_user
    read_json["comments"] = """ This series is part of the long term planktonic monitoring of
Villefranche-sur-mer, which is one of the oldest and richest in the world.
The data collection and processing has been funded by several projects
over its lifetime. It is currently supported directly by the Institut de la Mer
de Villefranche (IMEV), as part of its long term monitoring effort. """
    read_json["license"] = "CC BY 4.0"
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=read_json)
    assert rsp.status_code == status.HTTP_200_OK

    # Real User exports it
    req = EMODnetExportReq(project_ids=[prj_id])
    rsp = EMODnetExport(req, dry_run=True).run(REAL_USER_ID)
    assert rsp.errors == []
