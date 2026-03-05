from starlette import status

from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.test_admin import PROJECT_DIGEST_URL
from tests.test_import import do_import_uvp6

CLEANUP_URL = "/admin/images/cleanup1?project_id={project_id}"


def test_admin_images_cleanup(fastapi):
    # Prepare a project with some images
    prj_id = do_import_uvp6(fastapi, "Test Project Admin Images Cleanup1")

    url = PROJECT_DIGEST_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert isinstance(rsp.json(), str)
    assert "Digest for" in rsp.json()

    url = CLEANUP_URL.format(project_id=prj_id)

    # Simple user cannot access the admin cleanup endpoint
    rsp = fastapi.get(url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Admin can
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert isinstance(rsp.json(), str)
    assert rsp.json().startswith("Dupl remover for")
