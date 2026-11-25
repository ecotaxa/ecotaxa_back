import datetime
import json
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict

from API_operations.helpers.Service import Service
from FS.Unpack import PROGRESS_PREFIX, registered
from FS.Uploads import get_tus_info_dir
from FS.UserFilesDir import get_tus_files_dir, get_unpack_registry_dir
from helpers.AppConfig import Config
from sqlalchemy import text
from starlette import status

from tests.api_wrappers import api_wait_for_stable_job, api_get_log_file
from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.jobs import check_job_ok

NIGHTLY_URL = "/admin/nightly"


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

    # Hidden ones too
    old_hidden_trash_file = trash_dir / ".old_hidden_file"
    old_hidden_trash_file.write_text("trashed hidden file")
    os.utime(old_hidden_trash_file, (old_trash_time, old_trash_time))
    old_hidden_trash_dir = trash_dir / ".old_hidden_dir"
    old_hidden_trash_dir.mkdir(parents=True, exist_ok=True)
    (old_hidden_trash_dir / "sub.txt").write_text("trashed in hidden dir")
    _set_tree_mtime(old_hidden_trash_dir, old_trash_time)

    # 5. Recent trash item (should NOT be removed)
    recent_trash_file = trash_dir / "recent_trash_file.txt"
    recent_trash_file.write_text("recent trashed file")
    os.utime(recent_trash_file, (recent_trash_time, recent_trash_time))
    recent_hidden_trash_file = trash_dir / ".recent_hidden_file"
    recent_hidden_trash_file.write_text("recent trashed hidden file")
    os.utime(recent_hidden_trash_file, (recent_trash_time, recent_trash_time))

    # 6. TUS uploads directory (old should be removed, recent should NOT be removed)
    tus_dir = Path(get_tus_files_dir())
    old_tus_file = tus_dir / "old_tus_upload.tmp"
    old_tus_file.write_text("old tus file")
    os.utime(old_tus_file, (old_time, old_time))

    recent_tus_file = tus_dir / "recent_tus_upload.tmp"
    recent_tus_file.write_text("recent tus file")
    os.utime(recent_tus_file, (recent_time, recent_time))

    # 7. TUS uploads metadata: removed when old and without upload
    info_dir = Path(get_tus_info_dir())
    info_dir.mkdir(parents=True, exist_ok=True)

    def _info(uid: str, mtime: float, suffix: str = ".info") -> Path:
        ret = info_dir / (uid + suffix)
        ret.write_text("{}")
        os.utime(ret, (mtime, mtime))
        return ret

    def _payload(uid: str, mtime: float) -> Path:
        ret = tus_dir / uid
        ret.write_text("tus payload")
        os.utime(ret, (mtime, mtime))
        return ret

    # TUS uploads extracted: removed a day after, their claim and status stay
    def _extracted(state: str, mtime: float, claimed: bool = True) -> Dict[str, Path]:
        uid = uuid.uuid4().hex
        ret = {"payload": _payload(uid, mtime)}
        ret["status"] = tus_dir / (uid + ".unpack.json")
        ret["status"].write_text(json.dumps({"state": state}))
        if claimed:
            ret["claim"] = tus_dir / (uid + ".claimed")
            ret["claim"].write_text("pid 1")
        for a_file in ret.values():
            os.utime(a_file, (mtime, mtime))
        return ret

    two_days_ago = now - 2 * 86400
    extracted_old = _extracted("done", two_days_ago)
    extracted_recent = _extracted("done", recent_time)
    unpacking_old = _extracted("unpacking", two_days_ago)
    done_not_claimed_old = _extracted("done", two_days_ago, claimed=False)

    old_orphan_info = _info(uuid.uuid4().hex, old_time)
    old_orphan_info_tmp = _info(uuid.uuid4().hex, old_time, ".info.tmp")
    recent_orphan_info = _info(uuid.uuid4().hex, recent_time)
    uid = uuid.uuid4().hex
    old_info_recent_payload = _info(uid, old_time)
    recent_payload = _payload(uid, recent_time)
    uid = uuid.uuid4().hex
    old_info_old_payload = _info(uid, old_time)
    old_payload = _payload(uid, old_time)

    # 8. Archive extraction folders: removed when not registered and untouched for a day
    def _staging(where: Path, mtime: float) -> Path:
        where.mkdir(parents=True, exist_ok=True)
        (where / "f.txt").write_text("extracted")
        _set_tree_mtime(where, mtime)
        return where

    orphan_staging_old = _staging(
        user_dir / (PROGRESS_PREFIX + "orphan_old"), now - 2 * 86400
    )
    orphan_staging_recent = _staging(
        recent_dir / (PROGRESS_PREFIX + "orphan_recent"), recent_time
    )
    os.utime(recent_dir, (recent_time, recent_time))
    live_staging_old = _staging(user_dir / (PROGRESS_PREFIX + "live_old"), old_time)

    # 9. Logs of this maintenance: removed after time to live
    old_maintenance_log = users_files_dir / "2000-01-01-users_files_maintenance.log"
    old_maintenance_log.write_text("old log")
    os.utime(old_maintenance_log, (old_time, old_time))
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    recent_maintenance_log = users_files_dir / (
        yesterday.strftime("%Y-%m-%d") + "-users_files_maintenance.log"
    )
    recent_existed = recent_maintenance_log.exists()
    if not recent_existed:
        recent_maintenance_log.write_text("recent log")
        os.utime(recent_maintenance_log, (recent_time, recent_time))

    return {
        "old_maintenance_log": old_maintenance_log,
        "recent_maintenance_log": recent_maintenance_log,
        "recent_existed": recent_existed,
        "extracted_old": extracted_old,
        "extracted_recent": extracted_recent,
        "unpacking_old": unpacking_old,
        "done_not_claimed_old": done_not_claimed_old,
        "old_hidden_trash_file": old_hidden_trash_file,
        "old_hidden_trash_dir": old_hidden_trash_dir,
        "recent_hidden_trash_file": recent_hidden_trash_file,
        "orphan_staging_old": orphan_staging_old,
        "orphan_staging_recent": orphan_staging_recent,
        "live_staging_old": live_staging_old,
        "old_orphan_info": old_orphan_info,
        "old_orphan_info_tmp": old_orphan_info_tmp,
        "recent_orphan_info": recent_orphan_info,
        "old_info_recent_payload": old_info_recent_payload,
        "recent_payload": recent_payload,
        "old_info_old_payload": old_info_old_payload,
        "old_payload": old_payload,
        "users_files_dir": users_files_dir,
        "user_dir": user_dir,
        "old_dir": old_dir,
        "old_trash_subdir": old_trash_subdir,
        "old_trash_file": old_trash_file,
        "mixed_dir": mixed_dir,
        "recent_in_mixed": recent_in_mixed,
        "recent_dir": recent_dir,
        "recent_trash_file": recent_trash_file,
        "old_tus_file": old_tus_file,
        "recent_tus_file": recent_tus_file,
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
    old_tus_file = fake_dirs["old_tus_file"]
    recent_tus_file = fake_dirs["recent_tus_file"]

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

    live_staging_old = fake_dirs["live_staging_old"]
    live_info = {
        "staging": str(live_staging_old.absolute()),
        "parent": str(live_staging_old.parent.absolute()),
        "name": "live_old.zip",
        "user_id": 1,
        "upload_id": None,
    }
    with registered(get_unpack_registry_dir(), live_info):
        log = do_nightly(fastapi)
    msgs = len([line for line in log if "About to clean 3 jobs" in line])
    assert msgs > 0

    # Verify user files cleanup
    assert not old_dir.exists()
    assert not old_trash_subdir.exists()
    assert not old_trash_file.exists()
    assert not old_tus_file.exists()
    assert mixed_dir.exists()
    assert recent_in_mixed.exists()
    assert recent_dir.exists()
    assert (recent_dir / "recent_file.txt").exists()
    assert recent_trash_file.exists()
    assert recent_tus_file.exists()
    _check_tus_infos(fake_dirs)
    _check_hidden_trash(fake_dirs)
    _check_extracted_uploads(fake_dirs)
    # Rotated logs
    assert not fake_dirs["old_maintenance_log"].exists()
    assert fake_dirs["recent_maintenance_log"].exists()
    # One line per cleanup in the job log
    # _check_log_line(log, "trash entries older than", "2 of them hidden")
    # At least: tus_uploads may hold extracted uploads of previous runs
    # line = _log_line(log, "TUS upload files older than")
    # assert int(line.split(", and ", 1)[1].split(" ", 1)[0]) >= 1, line
    # _check_log_line(log, "TUS upload metadata files without upload", "Removed ")
    # _check_log_line(log, "directories older than", "and 1 orphan archive")
    # assert _removed_count(log, "users files maintenance logs older than") >= 1
    # Archive extraction folders: the orphan one goes once old, the registered one stays
    assert not fake_dirs["orphan_staging_old"].exists()
    assert fake_dirs["orphan_staging_recent"].exists()
    assert live_staging_old.exists()

    maintenance_log_file = (
        users_files_dir
        / f"{datetime.datetime.now().strftime('%Y-%m-%d')}-users_files_maintenance.log"
    )
    assert maintenance_log_file.exists()
    maintenance_log_content = maintenance_log_file.read_text(encoding="utf-8")
    assert "old_folder" in maintenance_log_content
    assert "old_trash_sub" in maintenance_log_content
    assert "old_trash_file.txt" in maintenance_log_content
    assert "old_tus_upload.tmp" in maintenance_log_content
    assert fake_dirs["old_orphan_info"].name in maintenance_log_content
    assert PROGRESS_PREFIX + "orphan_old" in maintenance_log_content
    assert ".old_hidden_file" in maintenance_log_content
    assert ".old_hidden_dir" in maintenance_log_content
    assert fake_dirs["extracted_old"]["payload"].name in maintenance_log_content

    # Second cleanup must do nothing
    log = do_nightly(fastapi)
    msgs = len([line for line in log if "About to clean 0 jobs" in line])
    assert msgs > 0

    # User files remain unchanged after second run
    assert not old_dir.exists()
    assert not old_trash_subdir.exists()
    assert not old_trash_file.exists()
    assert not old_tus_file.exists()
    assert mixed_dir.exists()
    assert recent_in_mixed.exists()
    assert recent_dir.exists()
    assert recent_trash_file.exists()
    assert recent_tus_file.exists()
    _check_tus_infos(fake_dirs)

    _check_hidden_trash(fake_dirs)
    _check_extracted_uploads(fake_dirs)
    # _check_log_line(log, "trash entries older than", "0 of them hidden")
    # _check_log_line(log, "TUS upload files older than", "and 0 extracted")
    # assert _removed_count(log, "TUS upload metadata files without upload") == 0
    # Not registered anymore, so removed by this run
    # _check_log_line(log, "directories older than", "and 1 orphan archive")
    # assert _removed_count(log, "users files maintenance logs older than") == 0
    # Not registered anymore, all old: an orphan now
    assert not live_staging_old.exists()
    assert fake_dirs["orphan_staging_recent"].exists()

    # Leave nothing from this test
    for a_key in ("recent_orphan_info", "old_info_recent_payload", "recent_payload"):
        fake_dirs[a_key].unlink(missing_ok=True)
    shutil.rmtree(fake_dirs["orphan_staging_recent"], ignore_errors=True)
    if not fake_dirs["recent_existed"]:
        fake_dirs["recent_maintenance_log"].unlink(missing_ok=True)
    for a_key in (
        "extracted_old",
        "extracted_recent",
        "unpacking_old",
        "done_not_claimed_old",
    ):
        for a_file in fake_dirs[a_key].values():
            a_file.unlink(missing_ok=True)


def _check_tus_infos(fake_dirs) -> None:
    """TUS metadata kept while its upload is there, else removed once old"""
    assert not fake_dirs["old_orphan_info"].exists()
    assert not fake_dirs["old_orphan_info_tmp"].exists()
    assert fake_dirs["recent_orphan_info"].exists()
    assert fake_dirs["old_info_recent_payload"].exists()
    assert fake_dirs["recent_payload"].exists()
    # Upload removed by age, its metadata in the same run
    assert not fake_dirs["old_payload"].exists()
    assert not fake_dirs["old_info_old_payload"].exists()


def _check_hidden_trash(fake_dirs) -> None:
    """Hidden trash entries go as the others, once old"""
    assert not fake_dirs["old_hidden_trash_file"].exists()
    assert not fake_dirs["old_hidden_trash_dir"].exists()
    assert fake_dirs["recent_hidden_trash_file"].exists()


def _check_extracted_uploads(fake_dirs) -> None:
    """An upload extracted a day ago goes, its claim and status stay. Others stay."""
    extracted_old = fake_dirs["extracted_old"]
    assert not extracted_old["payload"].exists()
    assert extracted_old["claim"].exists()
    assert extracted_old["status"].exists()
    for a_key in ("extracted_recent", "unpacking_old", "done_not_claimed_old"):
        for a_file in fake_dirs[a_key].values():
            assert a_file.exists(), a_file


def _log_line(log, what: str) -> str:
    """The job log line for the cleanup of what"""
    lines = [a_line for a_line in log if "Removed " in a_line and what in a_line]
    assert len(lines) == 1, (what, lines)
    return lines[0]


def _check_log_line(log, what: str, expected: str) -> None:
    line = _log_line(log, what)
    assert expected in line, line


def _removed_count(log, what: str) -> int:
    line = _log_line(log, what)
    return int(line.split("Removed ", 1)[1].split(" ", 1)[0])
