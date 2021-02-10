import logging

from starlette import status

from tests.credentials import ADMIN_AUTH, USER_AUTH

PROJECT_DIGEST_URL = "/admin/images/{project_id}/digest?max_digests=100"


def test_admin_images(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import_uvp6
    prj_id = test_import_uvp6(config, database, caplog, "Test Project Admin")

    url = PROJECT_DIGEST_URL.format(project_id=prj_id)

    # Simple user cannot
    rsp = fastapi.get(url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Admin can
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == "Digest for 30 images done."

    # TODO: some common error cases

    # md5 is persisted
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == "Digest for 0 images done."
