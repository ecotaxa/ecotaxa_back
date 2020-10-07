#
# TODO: Ensure https://github.com/ecotaxa/ecotaxa_back/commit/4f36584ac53fb01d9bb7a835f1b4c90238b86791 not again
#
import logging

from starlette import status
from API_operations.JsonDumper import JsonDumper
from BO.Project import ProjectBO

from tests.credentials import CREATOR_AUTH, ADMIN_USER_ID
from tests.test_import import test_api_import_images
import io

PROJECT_DELETE_URL = "/projects/{project_id}?only_objects={only_objects}"


def test_api_project_delete(config, database, fastapi, caplog):
    """
        Delete project in full or partially.
    """
    prj_id = test_api_import_images(config, database, fastapi, caplog, title="Project delete")
    url = PROJECT_DELETE_URL.format(project_id=prj_id, only_objects=True)
    rsp = fastapi.delete(url)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    rsp = fastapi.delete(url, headers=CREATOR_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    # Test emptyness
    with io.StringIO() as fd:
        JsonDumper(CREATOR_AUTH, prj_id, {}).run(fd)
        buff = fd.getvalue()
    assert buff == "{}"
