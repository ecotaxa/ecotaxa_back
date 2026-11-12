#
# Status of an upload unpacking, as reported while unpacking, and its shared store.
# No entry-by-entry extraction: progress moves only between archives and during
# the per-entry check after extractall().
#
from pathlib import Path

import pytest

import FS.UnpackStatus as UnpackStatusModule
from FS.UnpackStatus import UnpackStatus
from tests.userfiles_helpers import make_user_dir, zip_bytes, tree, TSV


def _setup(tmp_path: Path):
    root = tmp_path / "user"
    parent = root / "up"
    parent.mkdir(parents=True)
    return root, parent


def _recorded(root: Path):
    user_dir = make_user_dir(root)
    statuses = []
    user_dir.status_reporter = statuses.append
    return user_dir, statuses


def _corrupt(content: bytes) -> bytes:
    return content[:40] + b"\x00" * 40 + content[80:]


def test_status_nested_archives(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"ecotaxa_s.tsv": TSV, "x.tsv": TSV})
    archive = parent / "name.zip"
    archive.write_bytes(
        zip_bytes({"s1_Images.zip": inner, "s2_Images.zip": inner, "s3_Images.zip": inner})
    )
    user_dir, statuses = _recorded(root)
    user_dir.dispatch_unpack(archive, parent)
    states = [a_status["state"] for a_status in statuses]
    assert states[0] == "unpacking" and states[-1] == "done"
    assert set(states[:-1]) == {"unpacking"}
    percents = [a_status["percent"] for a_status in statuses]
    assert percents == sorted(percents), "percent only goes up"
    assert percents[-1] == 100 and max(percents[:-1]) < 100
    # Moves between the nested archives
    assert len(set(percents)) >= 4
    last = statuses[-1]
    assert last["name"] == "name.zip"
    assert last["entries_total"] == 3 and last["entries_done"] == 3
    # 3 entries in the upload, 2 in each nested archive
    assert last["files_done"] == 3 + 3 * 2
    assert last["bytes_done"] == 3 * len(inner) + 3 * 2 * len(TSV)
    assert last["bytes_declared"] == 3 * len(inner)
    assert last["result_paths"] == ["up/name"]
    assert "up/name/s1_Images/x.tsv" in tree(root)


def test_status_error(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"x.tsv": TSV * 50})
    archive = parent / "name.zip"
    archive.write_bytes(zip_bytes({"a.tsv": TSV, "in.zip": _corrupt(inner)}))
    user_dir, statuses = _recorded(root)
    with pytest.raises(Exception):
        user_dir.dispatch_unpack(archive, parent)
    last = statuses[-1]
    assert last["state"] == "error"
    assert "Archive is corrupt" in last["message"]
    assert str(root) not in last["message"]
    assert "result_paths" not in last


def test_status_flat_archive_limit(tmp_path):
    root, parent = _setup(tmp_path)
    archive = parent / "name.zip"
    archive.write_bytes(zip_bytes({"%d.tsv" % num: TSV for num in range(10)}))
    user_dir, statuses = _recorded(root)
    user_dir.dispatch_unpack(archive, parent)
    # The first statuses after reading the headers: all files are counted (declared),
    # but the percent is still 0, extractall() gives no progress
    with_total = [a_status for a_status in statuses if "entries_total" in a_status]
    assert with_total[0]["percent"] == 0 and with_total[0]["files_done"] == 10
    assert statuses[-1]["percent"] == 100


def test_no_reporter_no_status(tmp_path):
    root, parent = _setup(tmp_path)
    archive = parent / "name.zip"
    archive.write_bytes(zip_bytes({"a.tsv": TSV}))
    user_dir = make_user_dir(root)
    user_dir.dispatch_unpack(archive, parent)
    assert user_dir._status_fields == {}
    assert tree(parent) == ["name/", "name/a.tsv"]


#
# Shared store
#
@pytest.fixture
def tus_dir(tmp_path, monkeypatch):
    ret = tmp_path / "tus"
    ret.mkdir()
    monkeypatch.setattr(UnpackStatusModule, "get_tus_files_dir", lambda: str(ret))
    return ret


def test_store_write_read(tus_dir):
    status = UnpackStatus("fd8d989adda14069ba8495a71af1d6b8", 3, "a.zip")
    status.update({"state": "unpacking", "percent": 0})
    read = UnpackStatus.read("fd8d989adda14069ba8495a71af1d6b8")
    assert read is not None
    assert read["user_id"] == 3 and read["name"] == "a.zip"
    assert read["state"] == "unpacking" and "updated" in read
    # Atomic: only the final file, no temporary left
    assert [a_file.name for a_file in tus_dir.iterdir()] == [
        "fd8d989adda14069ba8495a71af1d6b8" + UnpackStatus.SUFFIX
    ]


def test_store_throttled_except_state_change(tus_dir, monkeypatch):
    status = UnpackStatus("abc", 3, "a.zip")
    status.update({"state": "unpacking", "percent": 0})
    status.update({"state": "unpacking", "percent": 50})
    read = UnpackStatus.read("abc")
    assert read is not None and read["percent"] == 0  # Throttled
    status.update({"state": "done", "percent": 100})
    read = UnpackStatus.read("abc")
    assert read is not None and read["state"] == "done"  # State change, written
    monkeypatch.setattr(UnpackStatus, "MIN_INTERVAL", 0)
    status.update({"state": "done", "percent": 100, "result_paths": ["x"]})
    read = UnpackStatus.read("abc")
    assert read is not None and read["result_paths"] == ["x"]


@pytest.mark.parametrize("upload_id", ["../../etc/passwd", "a/b", "", "x" * 65])
def test_store_invalid_ids(tus_dir, upload_id):
    with pytest.raises(ValueError):
        UnpackStatus(upload_id, 3, "a.zip")
    assert UnpackStatus.read(upload_id) is None


def test_store_unknown_id(tus_dir):
    assert UnpackStatus.read("nothere") is None
