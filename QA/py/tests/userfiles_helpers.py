#
# Helpers for My Files unpacking tests, without DB nor config.ini
#
import base64
import io
import zipfile
from pathlib import Path
from typing import Dict, List

from FS.UserFilesDir import UserFilesDirectory
from helpers.AppConfig import Config

# A valid 1x1 PNG, recognized by magic_rs
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
TSV = b"object_id\n[t]\nobj1\n"


def make_user_dir(root: Path) -> UserFilesDirectory:
    """A UserFilesDirectory rooted at root, without Config()"""
    ret = object.__new__(UserFilesDirectory)
    ret.accepted_mime_types = [m.strip() for m in Config.DEFAULT_MIMETYPES.split(",")]
    ret.archive_extensions = [a.strip() for a in Config.DEFAULT_ARCHIVES.split(",")]
    ret.user_id = 1
    ret.list_errors = {}
    ret._root_path = root
    ret.trash_directory = UserFilesDirectory.TRASH_DIRECTORY % 1
    ret.compressed_origin = None
    ret.report_to_file = False
    # Limits, generous by default, tests lower them
    ret.max_unpacked_size = 10**12
    ret.max_unpack_depth = 5
    ret.max_unpack_entries = 10**6
    # No check of free disk space
    ret.min_free_disk_ratio, ret.min_free_disk_bytes = None, 0
    ret._reset_unpack_budget()
    ret.status_reporter = None
    # No registration of unpackings, tests set it
    ret.registry_dir = None
    ret.upload_id = None
    ret._status_fields = {}
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
