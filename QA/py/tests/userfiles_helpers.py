#
# Helpers for My Files unpacking tests, without DB nor config.ini
#
import base64
import io
import zipfile
from pathlib import Path
from typing import Dict, List

from API_models.constants import DEFAULT_ARCHIVES, DEFAULT_MIMETYPES
from FS.Unpack import Unpacker
from FS.UserFilesDir import UserFilesDirectory

# A valid 1x1 PNG, recognized by magic_rs
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
TSV = b"object_id\n[t]\nobj1\n"


def make_user_dir(root: Path) -> UserFilesDirectory:
    """A UserFilesDirectory rooted at root, without Config()"""
    ret = object.__new__(UserFilesDirectory)
    ret.user_id = 1
    ret._root_path = root
    ret.trash_directory = UserFilesDirectory.TRASH_DIRECTORY % 1
    unpacker = object.__new__(Unpacker)
    unpacker.accepted_mime_types = set(DEFAULT_MIMETYPES)
    unpacker.archive_extensions = {a.lower() for a in DEFAULT_ARCHIVES}
    unpacker.user_id = ret.user_id
    unpacker.list_errors = {}
    unpacker._root_path = root
    unpacker.compressed_origin = None
    unpacker.report_to_file = False
    # Limits, generous by default, tests lower them
    unpacker.max_unpacked_size = 10**12
    unpacker.max_unpack_depth = 5
    unpacker.max_unpack_entries = 10**6
    # No check of free disk space
    unpacker.min_free_disk_ratio, unpacker.min_free_disk_bytes = None, 0
    unpacker._reset_unpack_budget()
    unpacker.status_reporter = None
    # No registration of unpackings, tests set it
    unpacker.registry_dir = None
    unpacker.upload_id = None
    unpacker._status_fields = {}
    ret.unpacker = unpacker
    return ret


def zip_bytes(members: Dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)
    return buf.getvalue()


def tree(base: Path) -> List[str]:
    """Sorted relative listing, dirs with trailing /"""
    ret = []
    for a_path in base.rglob("*"):
        rel = a_path.relative_to(base).as_posix()
        ret.append(rel + "/" if a_path.is_dir() else rel)
    return sorted(ret)
