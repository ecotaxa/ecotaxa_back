import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from helpers.CustomException import UnprocessableEntityException
from FS.Unpack import Unpacker  # ou Unpack_3 selon le nom du module


def _make_tgz_bytes(entries: dict[str, bytes]) -> bytes:
    """Create an in-memory .tgz archive from {arcname: content}."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in entries.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _make_zip_bytes(entries: dict[str, bytes]) -> bytes:
    """Create an in-memory .zip archive from {arcname: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_nested_tgz_inside_zip(tmp_path: Path) -> None:
    """
    A .tgz embedded inside a .zip is extracted as a regular file by FilteredZipFile,
    then unpacked in streaming mode by FilteredTarFile.
    With double seek() in FilteredTarFile.makefile(), this raises StreamError
    ('seeking backwards is not allowed') wrapped as 422 UnprocessableEntityException.
    """
    # Minimal valid JPEG SOI + APP0 header + payload
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 600
    fake_tsv = b"object_id\tobject_lat\n1\t43.7\n"
    fake_exe = b"MZ" + b"\x00" * 600

    tgz_data = _make_tgz_bytes(
        {
            "sample/img1.jpg": fake_jpeg,
            "sample/meta.tsv": fake_tsv,
            "sample/bad.exe": fake_exe,
        }
    )
    zip_data = _make_zip_bytes({"inner.tgz": tgz_data})

    user_dir = tmp_path / "user_files"
    user_dir.mkdir()
    registry_dir = tmp_path / "registry"
    upload_path = user_dir / "upload.zip"
    upload_path.write_bytes(zip_data)

    errors: dict[str, str] = {}
    unpacker = Unpacker(
        root_path=user_dir,
        user_id=1,
        list_errors=errors,
        registry_dir=registry_dir,
    )

    # Fails with UnprocessableEntityException (422: seeking backwards is not allowed)
    # when FilteredTarFile.makefile seeks + reads before super().makefile().
    unpacker.dispatch_unpack(upload_path, user_dir)

    # Expected state once fixed:
    assert (user_dir / "upload" / "inner" / "sample" / "img1.jpg").is_file()
    assert (user_dir / "upload" / "inner" / "sample" / "meta.tsv").is_file()
    assert not (user_dir / "upload" / "inner" / "sample" / "bad.exe").exists()
    assert not (user_dir / "upload" / "inner.tgz").exists()
