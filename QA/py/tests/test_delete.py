#
# TODO: Ensure https://github.com/ecotaxa/ecotaxa_back/commit/4f36584ac53fb01d9bb7a835f1b4c90238b86791 not again
#
import logging

from starlette import status
from API_operations.JsonDumper import JsonDumper
from BO.Project import ProjectBO

from tests.credentials import CREATOR_AUTH, ADMIN_AUTH, ADMIN_USER_ID
from test_fastapi import PROJECT_QUERY_URL
from tests.test_import import dump_project
from tests.test_import_simple import test_api_import_images
from tests.test_update_prj import PROJECT_UPDATE_URL
import io

PROJECT_DELETE_URL = "/projects/{project_id}?only_objects={only_objects}"
OBJECT_SET_DELETE_URL = "/object_set/"


def test_api_project_delete(fastapi, caplog):
    """
    Delete project in full or partially.
    """
    caplog.set_level(logging.INFO)
    prj_id = test_api_import_images(fastapi, title="Project delete")
    url = PROJECT_DELETE_URL.format(project_id=prj_id, only_objects=True)
    rsp = fastapi.delete(url)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    rsp = fastapi.delete(url, headers=CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    # Test emptiness
    with io.StringIO() as fd:
        dump_project(CREATOR_AUTH, prj_id, fd)
        buff = fd.getvalue()
    assert buff == "{}"
    nb_upds = len(
        [msg for msg in caplog.messages if msg.startswith("Could not remove")]
    )
    # There should be no problem removing the files
    assert nb_upds == 0


def test_api_project_full_delete(fastapi, caplog):
    """
    Delete project in full.
    """
    prj_id = test_api_import_images(fastapi, title="Project full delete")
    # Bug in v2.6.8: Saving settings prevents DB deletion
    rsp = fastapi.get(
        PROJECT_QUERY_URL.format(project_id=prj_id, manage=True), headers=ADMIN_AUTH
    )
    rsp = fastapi.put(
        PROJECT_UPDATE_URL.format(project_id=prj_id),
        headers=ADMIN_AUTH,
        json=rsp.json(),
    )
    assert rsp.status_code == status.HTTP_200_OK
    # Should be OK after fix
    url = PROJECT_DELETE_URL.format(project_id=prj_id, only_objects=False)
    rsp = fastapi.delete(url, headers=CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    # Test absence
    rsp = fastapi.delete(url, headers=CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_404_NOT_FOUND
