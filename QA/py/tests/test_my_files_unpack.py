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


#
# Extensions are compared case-insensitively
#
def test_uppercase_extensions_in_archive(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"x.tsv": TSV})
    archive = _upload(
        parent,
        "name.zip",
        zip_bytes(
            {"DATA.TSV": TSV, "b.Csv": TSV, "c.TXT": TSV, "IMG.PNG": PNG_1X1, "INNER.ZIP": inner}
        ),
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/DATA.TSV",
        "name/IMG.PNG",
        "name/INNER/",
        "name/INNER/x.tsv",
        "name/b.Csv",
        "name/c.TXT",
    ]


@pytest.mark.parametrize("name", ["TOP.TSV", "top.Txt", "Top.CSV"])
def test_uppercase_plain_upload_kept(tmp_path, name):
    root, parent = _setup(tmp_path)
    upload = _upload(parent, name, TSV)
    make_user_dir(root).dispatch_unpack(upload, parent)
    assert tree(parent) == [name]


#
# Compressed tars: .tgz, and compound extensions from ARCHIVE_EXTENSIONS
#
def _a_tar(mode: str) -> bytes:
    return _tar(mode, TSV)


def test_top_level_tgz(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "x.tgz", _a_tar("w:gz"))
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["x/", "x/a.tsv"]


@pytest.mark.parametrize(
    "name,mode,folder",
    [
        ("in.tgz", "w:gz", "in"),
        ("in.TGZ", "w:gz", "in"),
        ("in.tar.gz", "w:gz", "in.tar"),
        ("in.tar.bz2", "w:bz2", "in.tar"),
        ("in.tar.xz", "w:xz", "in.tar"),
    ],
)
def test_nested_compressed_tar(tmp_path, name, mode, folder):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, name: _a_tar(mode)})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        "name/" + folder + "/",
        "name/" + folder + "/a.tsv",
    ]


def test_nested_archive_type_not_configured(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "in.tar.bz2": _a_tar("w:bz2")})
    )
    user_dir = make_user_dir(root)
    user_dir.archive_extensions = ["zip", "tar", "gz"]
    user_dir.dispatch_unpack(archive, parent)
    # Not a configured archive type, and its MIME type is not accepted
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_nested_fake_tgz_removed(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "fake.tgz": b"not an archive"})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


#
# Limits of an upload once unpacked: size, entries, nesting depth, free disk space
#
from collections import namedtuple

import FS.UserFilesDir as UserFilesDirModule
from FS.UserFilesDir import InsufficientStorageException
from helpers.httpexception import (
    DETAIL_UNPACK_TOO_LARGE,
    DETAIL_UNPACK_TOO_MANY_ENTRIES,
    DETAIL_UNPACK_TOO_DEEP,
    DETAIL_UNPACK_NO_DISK_SPACE,
)


def _limited(root: Path, **limits) -> UserFilesDirectory:
    ret = make_user_dir(root)
    for a_key, a_val in limits.items():
        setattr(ret, a_key, a_val)
    return ret


def _refused(user_dir, archive, parent, detail, exc_class=UnprocessableEntityException):
    with pytest.raises(exc_class) as exc:
        user_dir.dispatch_unpack(archive, parent)
    assert exc.value.message.startswith(detail), exc.value.message
    _nothing_left(parent)


def test_size_limit_zip(tmp_path):
    root, parent = _setup(tmp_path)
    # Highly compressible, like a zip bomb
    archive = _upload(parent, "name.zip", _deflated_zip(b"\x00" * 100_000))
    assert archive.stat().st_size < 1000
    _refused(_limited(root, max_unpacked_size=50_000), archive, parent, DETAIL_UNPACK_TOO_LARGE)


def test_size_limit_ok_at_limit(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV}))
    _limited(root, max_unpacked_size=len(TSV)).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_size_limit_adds_nested(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"x.tsv": TSV * 100})
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV, "in.zip": inner}))
    # Each archive alone is under the limit, not all together
    outer_size = len(TSV) + len(inner)
    inner_size = len(TSV) * 100
    limit = max(outer_size, inner_size) + 10
    assert outer_size + inner_size > limit
    _refused(_limited(root, max_unpacked_size=limit), archive, parent, DETAIL_UNPACK_TOO_LARGE)


def test_size_limit_compressed_tar(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.tar.gz", _tar("w:gz", b"\x00" * 100_000))
    _refused(_limited(root, max_unpacked_size=50_000), archive, parent, DETAIL_UNPACK_TOO_LARGE)


def test_size_limit_gz_streamed(tmp_path):
    root, parent = _setup(tmp_path)
    # Not zeros: a gzipped stream of zeros is a valid (empty) tar
    archive = _upload(parent, "a.tsv.gz", gzip.compress(TSV * 200_000))
    _refused(_limited(root, max_unpacked_size=1_500_000), archive, parent, DETAIL_UNPACK_TOO_LARGE)


def test_entries_limit(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"x.tsv": TSV, "y.tsv": TSV})
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "b.tsv": TSV, "in.zip": inner})
    )
    # 3 in the upload, 2 in the nested archive
    _limited(root, max_unpack_entries=5).dispatch_unpack(archive, parent)
    assert len(tree(parent)) == 6
    root, parent = _setup(tmp_path / "again")
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "b.tsv": TSV, "in.zip": inner})
    )
    _refused(_limited(root, max_unpack_entries=4), archive, parent, DETAIL_UNPACK_TOO_MANY_ENTRIES)


def _nested_zips(depth: int) -> bytes:
    content = zip_bytes({"x.tsv": TSV})
    for _ in range(depth - 1):
        content = zip_bytes({"in.zip": content})
    return content


def test_depth_limit(tmp_path):
    root, parent = _setup(tmp_path)
    # Upload + 2 levels, as for UVP6: upload.zip / *Images.zip, plus one
    archive = _upload(parent, "name.zip", _nested_zips(3))
    _limited(root, max_unpack_depth=3).dispatch_unpack(archive, parent)
    assert "name/in/in/x.tsv" in tree(parent)
    root, parent = _setup(tmp_path / "again")
    archive = _upload(parent, "name.zip", _nested_zips(4))
    _refused(_limited(root, max_unpack_depth=3), archive, parent, DETAIL_UNPACK_TOO_DEEP)


_Usage = namedtuple("_Usage", "total used free")


def test_disk_space(tmp_path, monkeypatch):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV * 100}))
    # Less than 10% would be left
    monkeypatch.setattr(
        UserFilesDirModule.shutil,
        "disk_usage",
        lambda path: _Usage(10_000, 9_000, 1_000 + len(TSV) * 50),
    )
    _refused(
        _limited(root, min_free_disk_ratio=0.1),
        archive,
        parent,
        DETAIL_UNPACK_NO_DISK_SPACE,
        InsufficientStorageException,
    )
    # Unless the check is off, with a 0 margin
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV * 100}))
    _limited(root, min_free_disk_ratio=0.0).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_limit_reported_in_background(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", _deflated_zip(b"\x00" * 100_000))
    user_dir = _limited(root, max_unpacked_size=50_000)
    user_dir.switch_to_background()
    with pytest.raises(UnprocessableEntityException):
        user_dir.dispatch_unpack(archive, parent)
    error_file = "name.zip" + UserFilesDirectory.ERROR_FILE_SUFFIX
    assert tree(parent) == [error_file]
    assert DETAIL_UNPACK_TOO_LARGE in (parent / error_file).read_text()


def test_budget_is_per_upload(tmp_path):
    root, parent = _setup(tmp_path)
    user_dir = _limited(root, max_unpacked_size=len(TSV), max_unpack_entries=1)
    for a_name in ("a.zip", "b.zip"):
        archive = _upload(parent, a_name, zip_bytes({"x.tsv": TSV}))
        user_dir.dispatch_unpack(archive, parent)
    assert tree(parent) == ["a/", "a/x.tsv", "b/", "b/x.tsv"]


def test_zero_limits_mean_no_check(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"x.tsv": TSV, "y.tsv": TSV})
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV * 1000, "in.zip": inner})
    )
    _limited(root, max_unpacked_size=0, max_unpack_entries=0).dispatch_unpack(
        archive, parent
    )
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        "name/in/",
        "name/in/x.tsv",
        "name/in/y.tsv",
    ]


def test_zero_limits_gz_streamed(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "a.tsv.gz", gzip.compress(TSV * 200_000))
    _limited(root, max_unpacked_size=0).dispatch_unpack(archive, parent)
    assert tree(parent) == ["a.tsv"]


def test_disk_space_margin_in_bytes(tmp_path, monkeypatch):
    root, parent = _setup(tmp_path)
    size = len(TSV) * 100
    # 1 TB disk with 50 GB + size free: under a 10% margin, but just enough for a 50 GB one
    monkeypatch.setattr(
        UserFilesDirModule.shutil,
        "disk_usage",
        lambda path: _Usage(10**12, 10**12 - 50 * 10**9 - size, 50 * 10**9 + size),
    )
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV * 100}))
    _refused(
        _limited(root, min_free_disk_ratio=0.1),
        archive,
        parent,
        DETAIL_UNPACK_NO_DISK_SPACE,
        InsufficientStorageException,
    )
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV * 100}))
    _refused(
        _limited(root, min_free_disk_bytes=50 * 10**9 + 1),
        archive,
        parent,
        DETAIL_UNPACK_NO_DISK_SPACE,
        InsufficientStorageException,
    )
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV * 100}))
    _limited(root, min_free_disk_bytes=50 * 10**9).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_disk_space_zero_margin_no_check(tmp_path, monkeypatch):
    root, parent = _setup(tmp_path)

    def no_call(path):
        raise AssertionError("disk_usage should not be called")

    monkeypatch.setattr(UserFilesDirModule.shutil, "disk_usage", no_call)
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV}))
    _limited(root, min_free_disk_ratio=None, min_free_disk_bytes=0).dispatch_unpack(
        archive, parent
    )
    assert tree(parent) == ["name/", "name/a.tsv"]


#
# Target folder of an archive: its own name, next to it, all entries inside
#
def test_nested_wrapped_in_subfolder(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"inner/x.tsv": TSV})
    archive = _upload(parent, "name.zip", zip_bytes({"a.tsv": TSV, "sub/inner.zip": inner}))
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        "name/sub/",
        "name/sub/inner/",
        "name/sub/inner/x.tsv",
    ]


@pytest.mark.parametrize(
    "members",
    [
        {"name/a.tsv": TSV, "other.tsv": TSV},
        {"other.tsv": TSV, "name/a.tsv": TSV},
    ],
)
def test_partly_wrapped_all_inside(tmp_path, members):
    root, parent = _setup(tmp_path)
    archive = _upload(parent, "name.zip", zip_bytes(members))
    make_user_dir(root).dispatch_unpack(archive, parent)
    # Same result whatever the order, nothing outside name/
    assert tree(parent) == [
        "name/",
        "name/name/",
        "name/name/a.tsv",
        "name/other.tsv",
    ]


def test_macos_zip_stays_wrapped(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent,
        "name.zip",
        zip_bytes({"name/a.tsv": TSV, "__MACOSX/name/._a.tsv": b"\x00\x05\x16\x07"}),
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    # The macOS junk is not a reason to wrap again. It is extracted next to name/, as before.
    assert tree(parent) == [
        "__MACOSX/",
        "__MACOSX/name/",
        "__MACOSX/name/._a.tsv",
        "name/",
        "name/a.tsv",
    ]


def test_wrapped_tar_with_dir_entries(tmp_path):
    root, parent = _setup(tmp_path)
    archive = parent / "name.tar"
    with tarfile.open(archive, "w") as tar:
        a_dir = tarfile.TarInfo("name")
        a_dir.type = tarfile.DIRTYPE
        tar.addfile(a_dir)
        info = tarfile.TarInfo("name/a.tsv")
        info.size = len(TSV)
        tar.addfile(info, io.BytesIO(TSV))
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]
