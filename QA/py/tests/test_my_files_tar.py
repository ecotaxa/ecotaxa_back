#
# Tar archives unpacked in My Files: extraction is filtered ("data" filter),
# whatever the Python version default, so a tar cannot write outside the target.
#
import io
import tarfile
from pathlib import Path

import pytest

from FS.UserFilesDir import UserFilesDirectory
from helpers.AppConfig import Config


def _user_dir(root: Path) -> UserFilesDirectory:
    # No Config() / config.ini needed
    ret = object.__new__(UserFilesDirectory)
    ret.accepted_mime_types = [
        m.strip() for m in Config.DEFAULT_MIMETYPES.split(",")
    ]
    ret.archive_extensions = [a.strip() for a in Config.DEFAULT_ARCHIVES.split(",")]
    ret.user_id = 1
    ret.list_errors = {}
    ret._root_path = root
    ret.trash_directory = UserFilesDirectory.TRASH_DIRECTORY % 1
    ret.compressed_origin = None
    ret.mark_progress = lambda compressed_path: compressed_path
    ret.unmark_progress = lambda to_path: None
    return ret


def _add_file(tar: tarfile.TarFile, name: str, content: bytes = b"a\tb\n") -> None:
    info = tarfile.TarInfo(name)
    info.size = len(content)
    tar.addfile(info, io.BytesIO(content))


def _setup(tmp_path: Path):
    root = tmp_path / "user"
    target = root / "up"
    target.mkdir(parents=True)
    return root, target


def test_tar_extract_uses_data_filter(tmp_path, monkeypatch):
    root, target = _setup(tmp_path)
    archive = target / "cont.tar"
    with tarfile.open(archive, "w") as tar:
        _add_file(tar, "cont/ecotaxa_a.tsv")
    seen = []
    orig = tarfile.TarFile.extractall

    def spy(self, *args, **kwargs):
        seen.append(kwargs.get("filter"))
        return orig(self, *args, **kwargs)

    monkeypatch.setattr(tarfile.TarFile, "extractall", spy)
    _user_dir(root).dispatch_unpack(archive, target)
    assert seen == ["data"]
    assert (target / "cont" / "ecotaxa_a.tsv").is_file()
    assert not archive.exists()


@pytest.mark.parametrize("member", ["../escape.txt", "cont/../../escape.txt"])
def test_tar_traversal_rejected(tmp_path, member):
    root, target = _setup(tmp_path)
    archive = target / "cont.tar"
    with tarfile.open(archive, "w") as tar:
        _add_file(tar, member)
    with pytest.raises(tarfile.TarError):
        _user_dir(root).dispatch_unpack(archive, target)
    assert list(tmp_path.rglob("escape.txt")) == []


def test_tar_absolute_member_stays_inside(tmp_path):
    root, target = _setup(tmp_path)
    outside = tmp_path / "outside_abs.txt"
    archive = target / "cont.tar"
    with tarfile.open(archive, "w") as tar:
        _add_file(tar, outside.as_posix())
    # "data" filter either rejects or strips the leading /, never writes there
    try:
        _user_dir(root).dispatch_unpack(archive, target)
    except tarfile.TarError:
        pass
    assert not outside.exists()


def test_tar_symlink_outside_rejected(tmp_path):
    root, target = _setup(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    archive = target / "cont.tar"
    with tarfile.open(archive, "w") as tar:
        link = tarfile.TarInfo("cont/lnk")
        link.type = tarfile.SYMTYPE
        link.linkname = outside.as_posix()
        tar.addfile(link)
        _add_file(tar, "cont/lnk/pwned.txt")
    with pytest.raises(tarfile.TarError):
        _user_dir(root).dispatch_unpack(archive, target)
    assert list(outside.iterdir()) == []
