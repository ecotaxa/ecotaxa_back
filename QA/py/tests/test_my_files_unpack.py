#
# My Files unpacking: resulting layout on success.
# These freeze the layout produced before extraction was staged, it must not change.
#
from pathlib import Path

from tests.userfiles_helpers import make_user_dir, zip_bytes, tree, TSV, PNG_1X1


def _setup(tmp_path: Path):
    root = tmp_path / "user"
    parent = root / "up"
    parent.mkdir(parents=True)
    return root, parent


def _upload(parent: Path, name: str, content: bytes) -> Path:
    archive = parent / name
    archive.write_bytes(content)
    return archive


def test_zip_root_members(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "img/x.png": PNG_1X1})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv", "name/img/", "name/img/x.png"]


def test_zip_already_wrapped(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"name/a.tsv": TSV, "name/x.png": PNG_1X1})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv", "name/x.png"]


def test_zip_nested(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"ecotaxa_inner.tsv": TSV, "x.png": PNG_1X1})
    archive = _upload(
        parent,
        "name.zip",
        zip_bytes({"a.tsv": TSV, "sub/inner_Images.zip": inner, "top.zip": inner}),
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        "name/sub/",
        "name/sub/inner_Images/",
        "name/sub/inner_Images/ecotaxa_inner.tsv",
        "name/sub/inner_Images/x.png",
        "name/top/",
        "name/top/ecotaxa_inner.tsv",
        "name/top/x.png",
    ]


def test_zip_unaccepted_member_removed(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "evil.bin": b"\x7fELF\x02\x01"})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_zip_onto_existing_folder(tmp_path):
    root, parent = _setup(tmp_path)
    (parent / "name").mkdir()
    (parent / "name" / "old.tsv").write_bytes(TSV)
    (parent / "name" / "a.tsv").write_bytes(b"replaced\n")
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "img/x.png": PNG_1X1})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        "name/img/",
        "name/img/x.png",
        "name/old.tsv",
    ]
    assert (parent / "name" / "a.tsv").read_bytes() == TSV


#
# Failure: all or nothing, the archive and any partial output are removed.
#
import io
import tarfile

import pytest

from FS.UserFilesDir import UserFilesDirectory, PROGRESS_PREFIX


def _nothing_left(parent: Path):
    assert tree(parent) == []


def _corrupt_zip() -> bytes:
    """Still detected as a zip (central directory intact), but data is corrupted"""
    content = zip_bytes({"a.tsv": TSV, "img/x.png": PNG_1X1 * 50})
    return content[:40] + b"\x00" * 40 + content[80:]


def test_truncated_zip(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", _corrupt_zip())
    with pytest.raises(Exception):
        make_user_dir(root).dispatch_unpack(archive, parent)
    _nothing_left(parent)


def test_corrupt_nested_zip(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"ecotaxa_inner.tsv": TSV * 20})
    bad_inner = inner[:40] + b"\x00" * 30 + inner[70:]
    archive = _upload(
        parent,
        "name.zip",
        zip_bytes({"a.tsv": TSV, "x.png": PNG_1X1, "sub/inner_Images.zip": bad_inner}),
    )
    with pytest.raises(Exception):
        make_user_dir(root).dispatch_unpack(archive, parent)
    _nothing_left(parent)


def test_refused_tar_member(tmp_path):
    root, parent = _setup(tmp_path)
    archive = parent / "name.tar"
    with tarfile.open(archive, "w") as tar:
        for a_name in ("a.tsv", "../escape.tsv"):
            info = tarfile.TarInfo(a_name)
            info.size = len(TSV)
            tar.addfile(info, io.BytesIO(TSV))
    with pytest.raises(tarfile.TarError):
        make_user_dir(root).dispatch_unpack(archive, parent)
    _nothing_left(parent)
    assert list(tmp_path.rglob("escape.tsv")) == []


def test_failure_during_type_check(tmp_path, monkeypatch):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent,
        "name.zip",
        zip_bytes({"a.tsv": TSV, "b.tsv": TSV, "c.tsv": TSV}),
    )
    orig = UserFilesDirectory._get_file_info
    calls = []

    def failing(filename, path):
        calls.append(filename)
        if len(calls) == 2:
            raise OSError("No space left on device")
        return orig(filename, path)

    monkeypatch.setattr(UserFilesDirectory, "_get_file_info", staticmethod(failing))
    with pytest.raises(OSError):
        make_user_dir(root).dispatch_unpack(archive, parent)
    _nothing_left(parent)


def test_background_failure_reported(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", _corrupt_zip())
    user_dir = make_user_dir(root)
    user_dir.switch_to_background()
    with pytest.raises(Exception):
        user_dir.dispatch_unpack(archive, parent)
    assert tree(parent) == ["name.zip" + UserFilesDirectory.ERROR_FILE_SUFFIX]
    report = (parent / ("name.zip" + UserFilesDirectory.ERROR_FILE_SUFFIX)).read_text()
    assert "name.zip" in report
    assert "[" in report and "]" in report
    assert str(root) not in report
    # A later successful upload of the same name removes the report
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV}))
    user_dir.dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_sync_failure_not_reported_in_file(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", _corrupt_zip())
    with pytest.raises(Exception):
        make_user_dir(root).dispatch_unpack(archive, parent)
    _nothing_left(parent)


def test_staging_name_taken(tmp_path):
    root, parent = _setup(tmp_path)
    other = parent / (PROGRESS_PREFIX + "name")
    other.mkdir()
    (other / "other.tsv").write_bytes(TSV)
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV}))
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        PROGRESS_PREFIX + "name/",
        PROGRESS_PREFIX + "name/other.tsv",
    ]


def test_dir_over_file_collision(tmp_path):
    root, parent = _setup(tmp_path)
    (parent / "name").write_bytes(TSV)
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV}))
    with pytest.raises(Exception):
        make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name"]
    assert (parent / "name").read_bytes() == TSV
