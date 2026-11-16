#
# Registry of unpackings in progress, and the clean up after a dead process left
# a staging folder in the user's files.
#
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from FS import Unpack
from FS.Unpack import PROGRESS_PREFIX, Unpacker, UnpackStatus
from helpers.httpexception import DETAIL_UNPACK_INTERRUPTED
from tests.userfiles_helpers import make_user_dir, zip_bytes, tree, TSV

PY_DIR = Path(Unpack.__file__).parent.parent
UPLOAD_ID = "fd8d989adda14069ba8495a71af1d6b8"


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    users = tmp_path / "users"
    root = users / "ecotaxa_user.1"
    parent = root / "up"
    parent.mkdir(parents=True)
    registry = tmp_path / "tus" / ".unpacking"
    monkeypatch.setattr(
        Unpack, "get_tus_files_dir", lambda: str(tmp_path / "tus")
    )
    return users, root, parent, registry


def _entries(registry: Path):
    return sorted(registry.iterdir()) if registry.exists() else []


def _is_locked(entry: Path) -> bool:
    fd = os.open(entry, os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return False
    except BlockingIOError:
        return True
    finally:
        os.close(fd)


def _owner(registry: Path, staging: Path, parent: Path, then: str) -> subprocess.Popen:
    """Another process registering an unpacking, then exiting at once or staying alive"""
    info = {
        "staging": str(staging),
        "parent": str(parent),
        "name": "x.zip",
        "user_id": 1,
        "upload_id": UPLOAD_ID,
    }
    script = (
        "import os, sys, time\n"
        "from pathlib import Path\n"
        "from FS import Unpack\n"
        "with Unpack.registered(Path(sys.argv[1]), %r):\n"
        "    print('ready', flush=True)\n"
        "    %s\n" % (info, "os._exit(0)" if then == "die" else "time.sleep(60)")
    )
    env = dict(os.environ, PYTHONPATH=str(PY_DIR))
    proc = subprocess.Popen(
        [sys.executable, "-c", script, str(registry)],
        stdout=subprocess.PIPE,
        env=env,
        text=True,
    )
    assert proc.stdout is not None
    assert proc.stdout.readline().strip() == "ready"
    return proc


def _staging(parent: Path) -> Path:
    staging = parent / (PROGRESS_PREFIX + "x")
    (staging / "x").mkdir(parents=True)
    (staging / "x" / "a.tsv").write_bytes(TSV)
    return staging


def test_registered_while_unpacking(dirs):
    users, root, parent, registry = dirs
    user_dir = make_user_dir(root)
    user_dir.unpacker.registry_dir = registry
    user_dir.unpacker.upload_id = UPLOAD_ID
    seen = []

    def reporter(status):
        if status.get("state") == "unpacking":
            for an_entry in _entries(registry):
                seen.append((json.loads(an_entry.read_text()), _is_locked(an_entry)))

    user_dir.unpacker.status_reporter = reporter
    archive = parent / "name.zip"
    archive.write_bytes(zip_bytes({"a.tsv": TSV}))
    user_dir.unpacker.dispatch_unpack(archive, parent)
    assert seen, "Not registered"
    info, locked = seen[-1]
    assert locked
    assert info["name"] == "name.zip" and info["upload_id"] == UPLOAD_ID
    assert info["user_id"] == 1 and info["pid"] == os.getpid()
    assert Path(info["staging"]).name.startswith(PROGRESS_PREFIX)
    assert Path(info["parent"]) == parent.absolute()
    # Done: unregistered
    assert _entries(registry) == []
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_unregistered_after_failure(dirs):
    users, root, parent, registry = dirs
    user_dir = make_user_dir(root)
    user_dir.unpacker.registry_dir = registry
    archive = parent / "name.zip"
    good = zip_bytes({"a.tsv": TSV * 100})
    archive.write_bytes(good[:40] + b"\x00" * 40 + good[80:])
    with pytest.raises(Exception):
        user_dir.unpacker.dispatch_unpack(archive, parent)
    assert _entries(registry) == []


def test_registry_problem_does_not_prevent_unpack(dirs):
    users, root, parent, registry = dirs
    registry.parent.mkdir(parents=True)
    registry.write_text("not a directory")
    user_dir = make_user_dir(root)
    user_dir.unpacker.registry_dir = registry
    archive = parent / "name.zip"
    archive.write_bytes(zip_bytes({"a.tsv": TSV}))
    user_dir.unpacker.dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_dead_owner_cleaned_up(dirs):
    users, root, parent, registry = dirs
    staging = _staging(parent)
    proc = _owner(registry, staging, parent, "die")
    proc.wait(10)
    assert len(_entries(registry)) == 1
    assert Unpack.sweep_stale(registry, users) == 1
    error_file = "x.zip" + Unpacker.ERROR_FILE_SUFFIX
    assert tree(parent) == [error_file]
    message = "Extraction of 'x.zip' failed, nothing was kept: " + DETAIL_UNPACK_INTERRUPTED
    assert message in (parent / error_file).read_text()
    status = UnpackStatus.read(UPLOAD_ID)
    assert status is not None
    assert status["state"] == "error" and status["status_code"] == 500
    assert status["message"] == message and status["user_id"] == 1
    assert _entries(registry) == []
    # Nothing more to do
    assert Unpack.sweep_stale(registry, users) == 0


def test_live_owner_left_alone(dirs):
    users, root, parent, registry = dirs
    staging = _staging(parent)
    proc = _owner(registry, staging, parent, "live")
    try:
        assert Unpack.sweep_stale(registry, users) == 0
        assert staging.is_dir() and len(_entries(registry)) == 1
    finally:
        proc.kill()
        proc.wait(10)
    # Its process is gone now
    assert Unpack.sweep_stale(registry, users) == 1
    assert not staging.exists()


def test_own_live_entry_left_alone(dirs):
    users, root, parent, registry = dirs
    staging = _staging(parent)
    info = {"staging": str(staging), "parent": str(parent), "name": "x.zip"}
    with Unpack.registered(registry, info):
        assert Unpack.sweep_stale(registry, users) == 0
        assert staging.is_dir()
    assert _entries(registry) == []


@pytest.mark.parametrize("where", ["outside", "no_prefix"])
def test_unexpected_staging_not_removed(dirs, tmp_path, where):
    users, root, parent, registry = dirs
    if where == "outside":
        staging = tmp_path / "elsewhere" / (PROGRESS_PREFIX + "x")
    else:
        staging = parent / "x"
    staging.mkdir(parents=True)
    registry.mkdir(parents=True)
    entry = registry / ("0" * 32 + Unpack.SUFFIX)
    entry.write_text(
        json.dumps({"staging": str(staging), "parent": str(parent), "name": "x.zip"})
    )
    assert Unpack.sweep_stale(registry, users) == 1
    assert staging.is_dir()
    assert _entries(registry) == []


def test_unreadable_and_old_temp_entries_dropped(dirs):
    users, root, parent, registry = dirs
    registry.mkdir(parents=True)
    (registry / ("1" * 32 + Unpack.SUFFIX)).write_text("{not json")
    old_tmp = registry / ("abc" + Unpack.TMP_SUFFIX)
    old_tmp.write_text("")
    os.utime(old_tmp, (0, 0))
    new_tmp = registry / ("def" + Unpack.TMP_SUFFIX)
    new_tmp.write_text("")
    Unpack.sweep_stale(registry, users)
    # A recent temporary one may be about to be published
    assert _entries(registry) == [new_tmp]


def test_no_registry_dir(tmp_path):
    assert Unpack.sweep_stale(tmp_path / "none", tmp_path) == 0
