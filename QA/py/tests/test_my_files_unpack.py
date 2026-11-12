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
from helpers.CustomException import UnprocessableEntityException
from helpers.httpexception import (
    DETAIL_CORRUPT_ARCHIVE,
    DETAIL_ARCHIVE_MEMBER_REFUSED,
    DETAIL_NOTHING_DONE,
)


def _nothing_left(parent: Path):
    assert tree(parent) == []


def _corrupt_zip() -> bytes:
    """Still detected as a zip (central directory intact), but data is corrupted"""
    content = zip_bytes({"a.tsv": TSV, "img/x.png": PNG_1X1 * 50})
    return content[:40] + b"\x00" * 40 + content[80:]


def test_truncated_zip(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", _corrupt_zip())
    with pytest.raises(UnprocessableEntityException) as exc:
        make_user_dir(root).dispatch_unpack(archive, parent)
    assert exc.value.message.startswith(DETAIL_CORRUPT_ARCHIVE)
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
    with pytest.raises(UnprocessableEntityException) as exc:
        make_user_dir(root).dispatch_unpack(archive, parent)
    assert exc.value.message.startswith(DETAIL_CORRUPT_ARCHIVE)
    _nothing_left(parent)


def test_refused_tar_member(tmp_path):
    root, parent = _setup(tmp_path)
    archive = parent / "name.tar"
    with tarfile.open(archive, "w") as tar:
        for a_name in ("a.tsv", "../escape.tsv"):
            info = tarfile.TarInfo(a_name)
            info.size = len(TSV)
            tar.addfile(info, io.BytesIO(TSV))
    with pytest.raises(UnprocessableEntityException) as exc:
        make_user_dir(root).dispatch_unpack(archive, parent)
    assert exc.value.message.startswith(DETAIL_ARCHIVE_MEMBER_REFUSED)
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
    with pytest.raises(UnprocessableEntityException):
        user_dir.dispatch_unpack(archive, parent)
    assert tree(parent) == ["name.zip" + UserFilesDirectory.ERROR_FILE_SUFFIX]
    report = (parent / ("name.zip" + UserFilesDirectory.ERROR_FILE_SUFFIX)).read_text()
    assert "name.zip" in report
    assert "[UnprocessableEntityException] " + DETAIL_CORRUPT_ARCHIVE in report
    assert str(root) not in report
    # A later successful upload of the same name removes the report
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV}))
    user_dir.dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_sync_failure_not_reported_in_file(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", _corrupt_zip())
    with pytest.raises(UnprocessableEntityException) as exc:
        make_user_dir(root).dispatch_unpack(archive, parent)
    assert exc.value.message.startswith(DETAIL_CORRUPT_ARCHIVE)
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
    with pytest.raises(UnprocessableEntityException) as exc:
        make_user_dir(root).dispatch_unpack(archive, parent)
    assert exc.value.message == DETAIL_NOTHING_DONE
    assert tree(parent) == ["name"]
    assert (parent / "name").read_bytes() == TSV


#
# Plain (not archive) uploads: same type check as for archive members.
#
import gzip


@pytest.mark.parametrize("name", ["ecotaxa_a.tsv", "b.csv", "c.txt", "d.png"])
def test_plain_upload_accepted(tmp_path, name):
    root, parent = _setup(tmp_path)
    upload = _upload(parent, name, PNG_1X1 if name.endswith(".png") else TSV)
    make_user_dir(root).dispatch_unpack(upload, parent)
    assert tree(parent) == [name]


def test_plain_upload_refused(tmp_path):
    root, parent = _setup(tmp_path)
    upload = _upload(parent, "evil.bin", b"\x7fELF\x02\x01")
    make_user_dir(root).dispatch_unpack(upload, parent)
    # Sync: no report file, just removed
    _nothing_left(parent)


def test_plain_upload_refused_reported_in_background(tmp_path):
    root, parent = _setup(tmp_path)
    upload = _upload(parent, "evil.bin", b"\x7fELF\x02\x01")
    user_dir = make_user_dir(root)
    user_dir.switch_to_background()
    user_dir.dispatch_unpack(upload, parent)
    error_file = "evil.bin" + UserFilesDirectory.ERROR_FILE_SUFFIX
    assert tree(parent) == [error_file]
    report = (parent / error_file).read_text()
    assert "evil.bin" in report and "not accepted" in report
    assert str(root) not in report


def test_gzipped_tsv_kept(tmp_path):
    root, parent = _setup(tmp_path)
    upload = _upload(parent, "ecotaxa_a.tsv.gz", gzip.compress(TSV))
    make_user_dir(root).dispatch_unpack(upload, parent)
    assert tree(parent) == ["ecotaxa_a.tsv"]
    assert (parent / "ecotaxa_a.tsv").read_bytes() == TSV


#
# Empty archives
#
import zipfile
import zlib

from FS.UserFilesDir import EmptyArchiveException
from helpers.httpexception import DETAIL_EMPTY_ARCHIVE


def _empty_archive(parent: Path, kind: str) -> Path:
    archive = parent / ("name." + kind)
    if kind == "zip":
        zipfile.ZipFile(archive, "w").close()
    else:
        tarfile.open(archive, "w").close()
    return archive


@pytest.mark.parametrize("kind", ["zip", "tar"])
def test_empty_archive_refused(tmp_path, kind):
    root, parent = _setup(tmp_path)
    archive = _empty_archive(parent, kind)
    with pytest.raises(EmptyArchiveException):
        make_user_dir(root).dispatch_unpack(archive, parent)
    _nothing_left(parent)


def test_empty_archive_reported_in_background(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _empty_archive(parent, "zip")
    user_dir = make_user_dir(root)
    user_dir.switch_to_background()
    with pytest.raises(EmptyArchiveException):
        user_dir.dispatch_unpack(archive, parent)
    error_file = "name.zip" + UserFilesDirectory.ERROR_FILE_SUFFIX
    assert tree(parent) == [error_file]
    report = (parent / error_file).read_text()
    assert "[EmptyArchiveException] " + DETAIL_EMPTY_ARCHIVE in report


def test_empty_nested_archive_dropped(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent,
        "name.zip",
        zip_bytes({"a.tsv": TSV, "sub/empty.zip": zip_bytes({})}),
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv", "name/sub/"]


#
# Other corrupt archive kinds: all a 422 "corrupt", nothing left
#
import os


def _deflated_zip(content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("a.tsv", content)
    return buf.getvalue()


def _tar(mode: str, content: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode=mode) as tar:
        info = tarfile.TarInfo("a.tsv")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


_RANDOM = os.urandom(2000) + TSV * 200


@pytest.mark.parametrize(
    "name,content,cause",
    [
        # Damaged deflate stream
        (
            "name.zip",
            _deflated_zip(TSV * 200)[:45] + b"\xff" * 20 + _deflated_zip(TSV * 200)[65:],
            zlib.error,
        ),
        ("name.tar", _tar("w", TSV * 200)[:700], tarfile.ReadError),
        ("name.tar.gz", _tar("w:gz", _RANDOM)[: len(_tar("w:gz", _RANDOM)) // 2], EOFError),
        ("a.tsv.gz", gzip.compress(TSV * 200)[:20], EOFError),
    ],
)
def test_corrupt_archive_kinds(tmp_path, name, content, cause):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, name, content)
    with pytest.raises(UnprocessableEntityException) as exc:
        make_user_dir(root).dispatch_unpack(archive, parent)
    assert exc.value.message.startswith(DETAIL_CORRUPT_ARCHIVE)
    assert isinstance(exc.value.__cause__, cause)
    _nothing_left(parent)
