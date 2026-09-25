import datetime
import logging
import os
import shutil
import time
from pathlib import Path

from API_operations.helpers.Service import Service
from helpers.AppConfig import Config
from sqlalchemy import text
from starlette import status

from tests.api_wrappers import api_wait_for_stable_job, api_get_log_file
from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.jobs import check_job_ok
from tests.test_import import do_import_uvp6

PROJECT_DIGEST_URL = "/admin/images/{project_id}/digest?max_digests=100"
NIGHTLY_URL = "/admin/nightly"


def test_admin_images(fastapi):

    prj_id, _ = do_import_uvp6(fastapi, "Test Project Admin")

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


def do_nightly(fastapi):
    rsp = fastapi.get(NIGHTLY_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()
    job = api_wait_for_stable_job(fastapi, job_id)
    log = api_get_log_file(fastapi, job.id)
    if any(":ERROR" in line for line in log):
        print(log)
    check_job_ok(job)
    return log


def create_fake_users_directories(monkeypatch):
    """
    Build an example user file hierarchy with past and recent dates for testing nightly maintenance.
    """
    config = Config()
    users_files_dir = Path(config.get_users_files_dir())
    timetolive = int(config.get_time_to_live())
    trashtimetolive = timetolive / 10 if timetolive >= 1 else 1

    user_id = 1
    user_dir = users_files_dir / f"ecotaxa_user.{user_id}"
    trash_dir = user_dir / f"trash.{user_id}"

    if user_dir.exists():
        shutil.rmtree(user_dir)

    now = time.time()
    old_time = now - (timetolive + 5) * 86400
    recent_time = now - 3600
    old_trash_time = now - (trashtimetolive + 2) * 86400
    recent_trash_time = now - 600

    def _set_tree_mtime(target: Path, mtime: float):
        for root, dirs, files in os.walk(target, topdown=False):
            for f in files:
                os.utime(os.path.join(root, f), (mtime, mtime))
            for d in dirs:
                os.utime(os.path.join(root, d), (mtime, mtime))
        os.utime(target, (mtime, mtime))

    # Mock os.path.getctime to return mtime for files/dirs inside user_dir
    orig_getctime = os.path.getctime

    def mock_getctime(path):
        try:
            p = Path(path).resolve()
            if users_files_dir.resolve() in p.parents or p == users_files_dir.resolve():
                return os.path.getmtime(path)
        except Exception:
            pass
        return orig_getctime(path)

    monkeypatch.setattr("os.path.getctime", mock_getctime)

    # 1. Old directory tree (all contents old -> should be removed)
    old_dir = user_dir / "old_folder"
    old_sub = old_dir / "sub_folder"
    old_sub.mkdir(parents=True, exist_ok=True)
    (old_sub / "old_subfile.txt").write_text("old sub content")
    (old_dir / "old_file.txt").write_text("old file content")
    _set_tree_mtime(old_dir, old_time)

    # 2. Partially old directory (dir is old, but contains a recent file -> should NOT be removed)
    mixed_dir = user_dir / "mixed_folder"
    mixed_dir.mkdir(parents=True, exist_ok=True)
    recent_in_mixed = mixed_dir / "recent_file.txt"
    recent_in_mixed.write_text("recent file in mixed")
    os.utime(recent_in_mixed, (recent_time, recent_time))
    os.utime(mixed_dir, (old_time, old_time))

    # 3. Recent directory (should NOT be removed)
    recent_dir = user_dir / "recent_folder"
    recent_dir.mkdir(parents=True, exist_ok=True)
    (recent_dir / "recent_file.txt").write_text("recent file content")
    _set_tree_mtime(recent_dir, recent_time)

    # 4. Old trash items (should be removed)
    trash_dir.mkdir(parents=True, exist_ok=True)
    old_trash_subdir = trash_dir / "old_trash_sub"
    old_trash_subdir.mkdir(parents=True, exist_ok=True)
    (old_trash_subdir / "subfile.txt").write_text("trashed subfile")
    _set_tree_mtime(old_trash_subdir, old_trash_time)

    old_trash_file = trash_dir / "old_trash_file.txt"
    old_trash_file.write_text("trashed file")
    os.utime(old_trash_file, (old_trash_time, old_trash_time))

    # 5. Recent trash item (should NOT be removed)
    recent_trash_file = trash_dir / "recent_trash_file.txt"
    recent_trash_file.write_text("recent trashed file")
    os.utime(recent_trash_file, (recent_trash_time, recent_trash_time))

    return {
        "users_files_dir": users_files_dir,
        "user_dir": user_dir,
        "old_dir": old_dir,
        "old_trash_subdir": old_trash_subdir,
        "old_trash_file": old_trash_file,
        "mixed_dir": mixed_dir,
        "recent_in_mixed": recent_in_mixed,
        "recent_dir": recent_dir,
        "recent_trash_file": recent_trash_file,
    }


def test_nightly_job(fastapi, caplog, tstlogs, mock_taxoserver, monkeypatch):
    # TODO: Not a real test, as we can't know in advance when the test runs, so the output
    # can't be verified against a reference.

    from test_export import test_export_roundtrip

    fake_dirs = create_fake_users_directories(monkeypatch)
    users_files_dir = fake_dirs["users_files_dir"]
    old_dir = fake_dirs["old_dir"]
    old_trash_subdir = fake_dirs["old_trash_subdir"]
    old_trash_file = fake_dirs["old_trash_file"]
    mixed_dir = fake_dirs["mixed_dir"]
    recent_in_mixed = fake_dirs["recent_in_mixed"]
    recent_dir = fake_dirs["recent_dir"]
    recent_trash_file = fake_dirs["recent_trash_file"]

    # Generate a few jobs however, and warp them back in time
    test_export_roundtrip(fastapi, tstlogs)  # Import/Export/Import
    with Service() as sce:
        sce.session.execute(
            text(
                "update job set creation_date='2022-06-01' where id in (select id from job order by id desc limit 3)"
            )
        )
        sce.session.commit()

    # Simple user cannot
    rsp = fastapi.get(NIGHTLY_URL, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Only Admin can
    caplog.set_level(logging.DEBUG)

    log = do_nightly(fastapi)
    msgs = len([line for line in log if "About to clean 3 jobs" in line])
    assert msgs > 0

    # Verify user files cleanup
    assert not old_dir.exists()
    assert not old_trash_subdir.exists()
    assert not old_trash_file.exists()
    assert mixed_dir.exists()
    assert recent_in_mixed.exists()
    assert recent_dir.exists()
    assert (recent_dir / "recent_file.txt").exists()
    assert recent_trash_file.exists()

    maintenance_log_file = (
        users_files_dir
        / f"{datetime.datetime.now().strftime('%Y-%m-%d')}-users_files_maintenance.log"
    )
    assert maintenance_log_file.exists()
    maintenance_log_content = maintenance_log_file.read_text(encoding="utf-8")
    assert "old_folder" in maintenance_log_content
    assert "old_trash_sub" in maintenance_log_content
    assert "old_trash_file.txt" in maintenance_log_content

    # Second cleanup must do nothing
    log = do_nightly(fastapi)
    msgs = len([line for line in log if "About to clean 0 jobs" in line])
    assert msgs > 0

    # User files remain unchanged after second run
    assert not old_dir.exists()
    assert not old_trash_subdir.exists()
    assert not old_trash_file.exists()
    assert mixed_dir.exists()
    assert recent_in_mixed.exists()
    assert recent_dir.exists()
    assert recent_trash_file.exists()
