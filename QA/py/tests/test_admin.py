import logging

from API_operations.helpers.Service import Service
from starlette import status

from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.export_shared import get_log_file
from tests.jobs import wait_for_stable, check_job_ok

PROJECT_DIGEST_URL = "/admin/images/{project_id}/digest?max_digests=100"
DIGEST_URL = "/admin/images/digest"
NIGHTLY_URL = "/admin/nightly"


def test_admin_images(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import_uvp6

    prj_id = test_import_uvp6(database, caplog, "Test Project Admin")

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

    rsp = fastapi.get(DIGEST_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == "Digest for 0 images done."


def do_nightly(fastapi):
    rsp = fastapi.get(NIGHTLY_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()
    job = wait_for_stable(job_id)
    log = str(get_log_file(fastapi, job.id))
    if ":ERROR" in log:
        print([a_line for a_line in log.split("\n")])
    check_job_ok(job)


def test_nightly_job(database, fastapi, caplog, tstlogs):
    # TODO: Not a real test, as we can't know in advance when the test runs, so the output
    # can't be verified against a reference.

    from test_export import test_export_roundtrip

    # Generate a few jobs however, and warp them back in time
    test_export_roundtrip(database, fastapi, caplog, tstlogs)  # Import/Export/Import
    with Service() as sce:
        sce.session.execute(
            "update job set creation_date='2022-06-01' where id in (select id from job order by id desc limit 3)"
        )
        sce.session.commit()

    # Simple user cannot
    rsp = fastapi.get(NIGHTLY_URL, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Only Admin can
    caplog.set_level(logging.DEBUG)

    do_nightly(fastapi)
    msgs = len(
        [msg for msg in caplog.messages if msg.startswith("About to clean 3 jobs")]
    )
    assert msgs > 0

    # Second cleanup must do nothing
    do_nightly(fastapi)
    msgs = len(
        [msg for msg in caplog.messages if msg.startswith("About to clean 0 jobs")]
    )
    assert msgs > 0
