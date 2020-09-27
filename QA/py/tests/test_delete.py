#
# TODO: Ensure https://github.com/ecotaxa/ecotaxa_back/commit/4f36584ac53fb01d9bb7a835f1b4c90238b86791 not again
#
import logging

from starlette import status

from tests.credentials import CREATOR_USER_ID, CREATOR_AUTH
from tests.test_import import test_api_import_images

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
    # TODO: Test emptyness
