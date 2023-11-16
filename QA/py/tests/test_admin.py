import logging

from starlette import status

from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.jobs import wait_for_stable, check_job_ok

PROJECT_DIGEST_URL = "/admin/images/{project_id}/digest?max_digests=100"
NIGHTLY_URL = "/admin/nightly"


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


def test_nightly_job(config, database, fastapi, caplog):
    # TODO: Not a real test, as we can't know in advance when the test runs, so the output
    # can't be verified against a reference.

    # Simple user cannot
    rsp = fastapi.get(NIGHTLY_URL, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Only Admin can
    caplog.set_level(logging.DEBUG)
    rsp = fastapi.get(NIGHTLY_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()
    job = wait_for_stable(job_id)
    check_job_ok(job)
