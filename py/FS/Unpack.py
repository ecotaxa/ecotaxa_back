# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import contextlib
import datetime
import fcntl
import gzip
import json
import os
import re
import shutil
import tarfile
import tempfile
import time
import uuid
import zipfile
import zlib
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union

from magic_rs import CantMatchTypeError, from_path

from API_models.constants import DEFAULT_ARCHIVES, DEFAULT_MIMETYPES
from DB.User import UserIDT
from helpers.AppConfig import Config
from helpers.CustomException import BaseAppException, UnprocessableEntityException
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_ARCHIVE_MEMBER_REFUSED,
    DETAIL_CORRUPT_ARCHIVE,
    DETAIL_EMPTY_ARCHIVE,
    DETAIL_FILE_TYPE_NOT_ACCEPTED,
    DETAIL_NOTHING_DONE,
    DETAIL_UNPACK_INTERRUPTED,
    DETAIL_UNPACK_NO_DISK_SPACE,
    DETAIL_UNPACK_TOO_DEEP,
    DETAIL_UNPACK_TOO_LARGE,
    DETAIL_UNPACK_TOO_MANY_ENTRIES,
)

logger = get_logger(__name__)

BUFFER_SIZE = 1024 * 1024
PROGRESS_PREFIX = "⌛"
# Additional accepted tabular/text formats, by extension, as magic detection can't type them
TEXT_EXTENSIONS = {
    "csv": "text/csv",
    "txt": "text/plain",
    "tsv": "text/tab-separated-values",
}

# What a broken archive, sent by the user, raises while being read
CORRUPT_ARCHIVE_EXCEPTIONS = (
    zipfile.BadZipFile,
    zlib.error,
    tarfile.TarError,
    gzip.BadGzipFile,
    EOFError,
)

# TUS upload ids are uuid4().hex
_UPLOAD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Registry of the archive unpackings in progress, shared between server processes.
SUFFIX = ".json"
TMP_SUFFIX = ".tmp"
# A temporary entry younger than this (s) may be about to be locked and published
TMP_GRACE = 60
# Entries held by this process. On NFS, flock is a per-process POSIX lock, so a
# sweep from the owning process would get the lock of a live entry.
_LIVE: Set[str] = set()
# The HTTP status of an interrupted unpacking, for status polling
INTERRUPTED_STATUS_CODE = 500


class EmptyArchiveException(UnprocessableEntityException):
    """An archive without any entry"""

    def __init__(self) -> None:
        super().__init__(DETAIL_EMPTY_ARCHIVE)


class InsufficientStorageException(BaseAppException):
    """Not the user's fault, the server disk is (almost) full"""

    def __init__(self, message: str):
        super().__init__(message, status_code=507)


class FileTypeRefusedException(UnprocessableEntityException):
    """An uploaded plain file, i.e. not an archive, of a type not accepted"""

    def __init__(self) -> None:
        super().__init__(DETAIL_FILE_TYPE_NOT_ACCEPTED)


def _unpack_exception_throw(e: Exception, context: Optional[str] = None) -> None:
    """
    During unpacking: a corrupt or refused archive is the user's problem, raise it as such (422).
    Other errors (e.g. disk full) are re-raised as they are.
    """
    if isinstance(e, BaseAppException):
        # Already qualified, e.g. from a nested archive
        raise e
    if isinstance(e, CORRUPT_ARCHIVE_EXCEPTIONS):
        error_detail = str(e) if str(e) else e.__class__.__name__
        if isinstance(e, tarfile.FilterError):
            message = f"{DETAIL_ARCHIVE_MEMBER_REFUSED}: {error_detail}"
        else:
            message = f"{DETAIL_CORRUPT_ARCHIVE}: {error_detail}"
        logger.error("422 " + message + " " + str(context))
        raise UnprocessableEntityException(message) from e
    _log_exception_throw(e, context)


def _log_exception_throw(e: Exception, context: Optional[str] = None) -> None:
    error_detail = str(e) if str(e) else repr(e)
    message = f"[{e.__class__.__name__}] {error_detail}"
    logger.error("500 " + message + " " + str(context))
    raise e


def get_tus_files_dir() -> str:
    """
    Get the directory where uploaded files (via TUS) are stored.
    Use a subfolder of the users files area.
    """
    base_dir = Config().get_users_files_dir()
    tus_dir = Path(base_dir, "tus_uploads")
    tus_dir.mkdir(parents=True, exist_ok=True)
    return str(tus_dir)


class FilteredZipFile(zipfile.ZipFile):
    """
    Subclass of ZipFile that filters extracted members during extract routines
    and collects embedded archives.
    """

    def __init__(
        self,
        *args: Any,
        filter_func: Callable[[str, Path], bool],
        is_embedded_archive: Callable[[str, Path], bool],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.filter_func = filter_func
        self.is_embedded_archive = is_embedded_archive
        self.embedded_archives: List[Path] = []

    def _extract_member(  # type: ignore[misc]
        self,
        member: Union[str, zipfile.ZipInfo],
        targetpath: str,
        pwd: Optional[bytes] = None,
    ) -> str:
        extracted_str: str = super()._extract_member(member, targetpath, pwd)  # type: ignore[misc]
        member_name = member.filename if isinstance(member, zipfile.ZipInfo) else member
        extracted_path = Path(extracted_str)
        if not self.filter_func(member_name, extracted_path):
            if extracted_path.is_file():
                extracted_path.unlink(missing_ok=True)
                logger.info("NOT EXTRACTED '%s' ", str(extracted_path))
        elif self.is_embedded_archive(member_name, extracted_path):
            self.embedded_archives.append(extracted_path)
        return extracted_str


class FilteredTarFile(tarfile.TarFile):
    """
    Subclass of TarFile that filters extracted members during extract routines
    and collects embedded archives.
    """

    def __init__(
        self,
        *args: Any,
        filter_func: Callable[[str, Path], bool],
        is_embedded_archive: Callable[[str, Path], bool],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.filter_func = filter_func
        self.is_embedded_archive = is_embedded_archive
        self.embedded_archives: List[Path] = []

    @classmethod
    def open(  # type: ignore[override]
        cls,
        *args: Any,
        filter_func: Callable[[str, Path], bool],
        is_embedded_archive: Callable[[str, Path], bool],
        **kwargs: Any,
    ) -> "FilteredTarFile":
        kwargs["filter_func"] = filter_func
        kwargs["is_embedded_archive"] = is_embedded_archive
        return super().open(*args, **kwargs)  # type: ignore[call-overload, no-any-return]

    def _extract_member(
        self,
        tarinfo: tarfile.TarInfo,
        targetpath: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super()._extract_member(tarinfo, targetpath, *args, **kwargs)
        extracted_path = Path(targetpath)
        if not self.filter_func(tarinfo.name, extracted_path):
            if extracted_path.is_file():
                extracted_path.unlink(missing_ok=True)
                logger.info("NOT EXTRACTED '%s' ", str(extracted_path))
        elif self.is_embedded_archive(tarinfo.name, extracted_path):
            self.embedded_archives.append(extracted_path)


class UnpackStatus(object):
    """
    Writer and reader of the status of one upload unpacking.
    """

    SUFFIX = ".unpack.json"
    # Minimum delay between two writes, unless the state changes
    MIN_INTERVAL = 0.5

    def __init__(self, upload_id: str, user_id: int, name: str):
        self.path = self.path_for(upload_id)
        self.base: Dict[str, Any] = {"user_id": user_id, "name": name}
        self._last_write = 0.0
        self._last_state: Optional[str] = None

    @classmethod
    def path_for(cls, upload_id: str) -> Path:
        if not _UPLOAD_ID_RE.match(upload_id):
            raise ValueError("Invalid upload id")
        return Path(get_tus_files_dir(), upload_id + cls.SUFFIX)

    def update(self, fields: Dict[str, Any]) -> None:
        """
        Write the status, at most every MIN_INTERVAL seconds unless the state changes. Never raises.
        """
        state = fields.get("state")
        now = time.monotonic()
        if state == self._last_state and now - self._last_write < self.MIN_INTERVAL:
            return
        data = dict(self.base)
        data.update(fields)
        data["updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            self._write_atomic(data)
        except Exception as e:
            logger.error("Could not write unpack status %s: %s", self.path, e)
            return
        self._last_write = now
        self._last_state = state

    def _write_atomic(self, data: Dict[str, Any]) -> None:
        # Readers in other processes see the previous version or this one, never a partial file
        fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=self.path.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as fout:
                json.dump(data, fout)
            os.replace(tmp_name, self.path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    @classmethod
    def read(cls, upload_id: str) -> Optional[Dict[str, Any]]:
        """The last written status, or None if unknown"""
        try:
            path = cls.path_for(upload_id)
            return json.loads(path.read_text())
        except (ValueError, OSError):
            return None


class Unpacker(object):
    """
    Handles unpacking of uploaded archives (zip, tar, gz) into user directories,
    checking limits, filtering entries, and reporting progress and errors.
    """

    ERROR_FILE_SUFFIX = ".unpack_error.log"
    PROGRESS_PREFIX = PROGRESS_PREFIX

    def __init__(
        self,
        root_path: Path,
        user_id: UserIDT,
        list_errors: Dict[str, str],
        registry_dir: Path,
    ):
        self.accepted_mime_types: Set[str] = set(DEFAULT_MIMETYPES)
        self.archive_extensions: Set[str] = {
            an_ext.lower() for an_ext in DEFAULT_ARCHIVES
        }
        self.user_id = user_id
        self._root_path = root_path
        self.list_errors: Dict[str, str] = list_errors
        self.compressed_origin: Optional[Path] = None
        # When set, an unpack failure is reported in a file next to the archive
        self.report_to_file = False
        # Where unpackings in progress are registered, to clean up after a restart
        self.registry_dir = registry_dir
        # The TUS upload being unpacked, if any
        self.upload_id: Optional[str] = None
        # Limits of one upload once unpacked, nested archives included
        config = Config()
        self.max_unpacked_size = config.get_max_unpacked_size()
        self.max_unpack_depth = config.get_max_unpack_depth()
        self.max_unpack_entries = config.get_max_unpack_entries()
        self.min_free_disk_ratio, self.min_free_disk_bytes = (
            config.get_unpack_min_free_disk()
        )
        self._reset_unpack_budget()
        # Optional, called with the unpack status as it changes, see _status
        self.status_reporter: Optional[Callable[[Dict[str, Any]], None]] = None
        self._status_fields: Dict[str, Any] = {}

    def switch_to_background(self) -> None:
        """Future unpacking operations run in background, nobody gets their exceptions,
        so report failures to the user in an error file."""
        self.report_to_file = True

    def extract_archive(
        self, archive: FilteredZipFile | FilteredTarFile, filepath: str, path: Path
    ) -> None:
        """
        Extract contents from an archive (zip or tar) into the target directory,
        handling subfolder placement, recursive decompression of nested archives,
        and filtering out unaccepted file formats.

        :param archive: An open ZipFile or TarFile archive instance.
        :param filepath: Full path of the archive file.
        :param path: Target directory Path where archive contents are to be extracted.
        :return: Relative subfolder path derived from the archive file name.
        """
        # Retrieve member file names based on archive type
        if isinstance(archive, zipfile.ZipFile):
            filenames = archive.namelist()
        else:
            filenames = archive.getnames()
        if len(filenames) == 0:
            raise EmptyArchiveException()
        # Check limits from what the archive declares, before writing anything
        if isinstance(archive, zipfile.ZipFile):
            declared_size = sum(an_info.file_size for an_info in archive.infolist())
        else:
            declared_size = sum(a_member.size for a_member in archive.getmembers())
        self._consume_unpack_budget(len(filenames), declared_size, path)
        top_level = self._unpack_depth == 1
        if top_level:
            self._status(entries_total=len(filenames), bytes_declared=declared_size)

        # The archive's own name, without its (last) extension, e.g. "inner" for sub/inner.zip
        archive_path = Path(filepath)
        own_name = ".".join(archive_path.name.split(".")[:-1])
        # macOS zips add __MACOSX/ entries, they don't tell if the content is wrapped
        checked = [a_name for a_name in filenames if not a_name.startswith("__MACOSX/")]
        # Extract next to the archive, into a folder with its name unless all entries
        # are already in such a folder. So nothing goes outside that folder.
        if own_name == "temp" and archive_path.parent == path:
            pass  # Zipfile sent by client, its content goes directly into path
        elif (
            own_name != ""
            and len(checked) > 0
            and all(
                a_name == own_name or a_name.startswith(own_name + "/")
                for a_name in checked
            )
        ):
            path = archive_path.parent  # Already wrapped
        else:
            path = archive_path.parent / own_name

        # Extract all files and directories into the target path
        if isinstance(archive, tarfile.TarFile):
            # No absolute paths, no escape out of path, no links outside, no devices
            archive.extractall(path.as_posix(), filter="data")
        else:
            archive.extractall(path.as_posix())

        # Unpack nested archives collected during extraction (no second pass required)
        for entry_idx, compressed_path in enumerate(archive.embedded_archives):
            if top_level:
                self._status_entries_done(entry_idx, len(filenames))
            if not compressed_path.exists():
                continue
            try:
                self._dispatch_nested(compressed_path, path)
            except EmptyArchiveException:
                # Nothing to keep from it, and it was removed. Not worth failing the whole upload.
                logger.info("Empty nested archive '%s' removed", compressed_path)

        if top_level:
            self._status_entries_done(len(filenames), len(filenames))

    def _is_embedded_archive(self, filename: str, filepath: Path) -> bool:
        return self._is_nested_archive(filename, filepath)

    def _is_accepted_extracted_file(self, filename: str, filepath: Path) -> bool:
        if filepath.is_dir():
            return True
        if self._is_embedded_archive(filename, filepath):
            return True
        file_ext, _, mime_type = self.get_file_info(filepath.name, filepath.parent)
        if file_ext in TEXT_EXTENSIONS:
            return True
        if mime_type in self.accepted_mime_types:
            return True
        return False

    def _is_nested_archive(self, filename: str, filepath: Path) -> bool:
        """
        Is the archive member an archive to unpack: its extension, possibly compound like
        "tar.gz" ("tgz" being "tar.gz"), is a configured archive one, and its content is an archive.
        """
        parts = filename.lower().rsplit("/", 1)[-1].split(".")
        if len(parts) < 2:
            return False
        candidates = [parts[-1]]
        if len(parts) >= 3:
            candidates.append(parts[-2] + "." + parts[-1])
        if parts[-1] == "tgz":
            candidates.append("tar.gz")
        if not any(c in self.archive_extensions for c in candidates):
            return False
        if not filepath.is_file():
            return False
        return self.is_compressed(filepath)

    @staticmethod
    def get_file_info(filename: str, path: Path) -> Tuple[str, Path, Optional[str]]:
        # Lowercase, extensions are compared case-insensitively
        file_ext = filename.split(".")[-1].lower()
        filepath = path.joinpath(filename)
        if filepath.is_dir():
            return file_ext, filepath, None
        if file_ext in TEXT_EXTENSIONS:
            return file_ext, filepath, TEXT_EXTENSIONS[file_ext]
        try:
            py_magic = from_path(str(filepath))
            mime_type = py_magic.mime_type()
        except (CantMatchTypeError, Exception):
            mime_type = None

        return file_ext, filepath, mime_type

    def _has_accepted_format(self, path: Path, filepath: str) -> bool:
        # Same extension fallback as for archive members
        if filepath.split(".")[-1].lower() in TEXT_EXTENSIONS:
            return True
        try:
            py_magic = from_path(filepath)
            mime_type = py_magic.mime_type()
        except (CantMatchTypeError, Exception):
            mime_type = None
        if mime_type in self.accepted_mime_types:
            return True
        logger.info(
            "File format not accepted '%s' '%s' , user_id '%s'",
            str(path),
            str(filepath),
            str(self.user_id),
        )
        path_error = str(path.joinpath(filepath.lstrip(os.path.sep)))
        self.list_errors.update({"Not accepted": path_error})
        return False

    def unpack_zip(self, input_path: Path, path: Path) -> None:
        try:
            with FilteredZipFile(
                input_path,
                "r",
                allowZip64=True,
                filter_func=self._is_accepted_extracted_file,
                is_embedded_archive=self._is_embedded_archive,
            ) as archive:
                self.extract_archive(archive, str(input_path), path)
        except Exception as e:
            _unpack_exception_throw(e, str(self.compressed_origin))
        finally:
            input_path.unlink(missing_ok=True)

    def unpack_tar(self, input_path: Path, path: Path) -> None:
        try:
            with FilteredTarFile.open(
                input_path,
                "r",
                filter_func=self._is_accepted_extracted_file,
                is_embedded_archive=self._is_embedded_archive,
            ) as archive:
                self.extract_archive(archive, str(input_path), path)
        except Exception as e:
            _unpack_exception_throw(e, str(self.compressed_origin))
        finally:
            input_path.unlink(missing_ok=True)

    def unpack_gz(self, input_path: Path, path: Path) -> None:
        decompressed_path = input_path.with_suffix("")
        try:
            # Size is unknown in advance, check limits while decompressing
            self._consume_unpack_budget(1, 0, path)
            with gzip.open(input_path, "rb") as f_in, open(
                decompressed_path, "wb"
            ) as f_out:
                while True:
                    chunk = f_in.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    self._consume_unpack_budget(0, len(chunk), path)
                    f_out.write(chunk)
            self._dispatch_nested(path / decompressed_path.name, path)
        except Exception as e:
            if decompressed_path.exists():
                decompressed_path.unlink()
            _unpack_exception_throw(e, str(self.compressed_origin))
        finally:
            input_path.unlink(missing_ok=True)

    def _reset_unpack_budget(self) -> None:
        self._unpacked_size = 0
        self._unpacked_entries = 0
        self._unpack_depth = 0
        self._bytes_since_last_disk_check = 0

    @contextlib.contextmanager
    def _one_level_deeper(self) -> Generator[None, None, None]:
        self._unpack_depth += 1
        try:
            # A 0 limit means no check
            if 0 < self.max_unpack_depth < self._unpack_depth:
                raise UnprocessableEntityException(
                    "%s (max. %d levels)"
                    % (DETAIL_UNPACK_TOO_DEEP, self.max_unpack_depth)
                )
            yield
        finally:
            self._unpack_depth -= 1

    def _consume_unpack_budget(self, nb_entries: int, size: int, where: Path) -> None:
        """
        Account for nb_entries / size bytes about to be written in where, raise if over a limit.
        """
        # A 0 limit means no check
        self._unpacked_entries += nb_entries
        if 0 < self.max_unpack_entries < self._unpacked_entries:
            raise UnprocessableEntityException(
                "%s (max. %d)"
                % (DETAIL_UNPACK_TOO_MANY_ENTRIES, self.max_unpack_entries)
            )
        self._unpacked_size += size
        self._status(files_done=self._unpacked_entries, bytes_done=self._unpacked_size)
        if 0 < self.max_unpacked_size < self._unpacked_size:
            raise UnprocessableEntityException(
                "%s (max. %d bytes)" % (DETAIL_UNPACK_TOO_LARGE, self.max_unpacked_size)
            )
        # A 0 margin means no check
        if size > 0 and (self.min_free_disk_ratio or self.min_free_disk_bytes):
            self._bytes_since_last_disk_check += size
            # Check on first allocation or when accumulated delta exceeds 32 MB
            if (
                self._bytes_since_last_disk_check >= 32 * 1024 * 1024
                or self._unpacked_size == size
            ):
                self._bytes_since_last_disk_check = 0
                usage = shutil.disk_usage(where)
                if self.min_free_disk_ratio is not None:
                    min_free = usage.total * self.min_free_disk_ratio
                else:
                    min_free = self.min_free_disk_bytes or 0
                if usage.free - size < min_free:
                    logger.error(
                        "Disk almost full, refusing to unpack %d bytes into %s",
                        size,
                        where,
                    )
                    raise InsufficientStorageException(DETAIL_UNPACK_NO_DISK_SPACE)

    @staticmethod
    def _new_staging_dir(parent: Path, archive: Path) -> Path:
        """
        Create a new, private, staging directory for unpacking archive into parent.
        Its name starts with PROGRESS_PREFIX so that the user sees the extraction in progress.
        """
        name = archive.name
        stem = name.rsplit(".", 1)[0] if "." in name else name
        base = PROGRESS_PREFIX + stem
        num = 1
        while True:
            candidate = parent / (base if num == 1 else "%s-%d" % (base, num))
            try:
                candidate.mkdir()
                return candidate
            except FileExistsError:
                num += 1

    @classmethod
    def _publish(cls, staging: Path, parent: Path) -> List[str]:
        """
        Move the content of the staging directory into parent, merging into existing directories.
        Return the published names.
        """
        published = list(staging.iterdir())
        for an_entry in published:
            cls._move_merging(an_entry, parent / an_entry.name)
        staging.rmdir()
        return sorted(an_entry.name for an_entry in published)

    @classmethod
    def _move_merging(cls, src: Path, dst: Path) -> None:
        src_is_dir = src.is_dir() and not src.is_symlink()
        dst_is_dir = dst.is_dir() and not dst.is_symlink()
        if not dst.exists() and not dst.is_symlink():
            src.rename(dst)
        elif src_is_dir and dst_is_dir:
            for a_child in list(src.iterdir()):
                cls._move_merging(a_child, dst / a_child.name)
            src.rmdir()
        elif not src_is_dir and not dst_is_dir:
            # File (or link) over file (or link): replace, as extractall does
            src.replace(dst)
        else:
            logger.error("Cannot publish %s over %s, not the same kind", src, dst)
            raise UnprocessableEntityException(DETAIL_NOTHING_DONE)

    @classmethod
    def _error_file(cls, parent: Path, archive_name: str) -> Path:
        return parent / (archive_name + cls.ERROR_FILE_SUFFIX)

    def unpack_failure(self, name: str, e: Exception) -> Tuple[int, str]:
        """
        The HTTP status code and the message, for the user, of e raised while unpacking
        the upload 'name'. The message has no server path, and no detail of server errors,
        which are in the logs.
        """
        if isinstance(e, BaseAppException):
            code, reason = e.status_code, e.message
            if self._root_path is not None:
                for a_root in (str(self._root_path.absolute()), str(self._root_path)):
                    reason = reason.replace(a_root, "")
        else:
            code, reason = 500, "unexpected server error"
        if isinstance(e, FileTypeRefusedException):
            return code, "Upload of '%s' refused: %s" % (name, reason)
        return code, "Extraction of '%s' failed, nothing was kept: %s" % (name, reason)

    def _report_failure(self, parent: Path, archive_name: str, e: Exception) -> None:
        """
        Tell, in the status and if in background in a file, why the upload produced nothing.
        Never raises.
        """
        code, message = self.unpack_failure(archive_name, e)
        self._report(parent, archive_name, "{when} UTC %s\n" % message)
        self._status(state="error", status_code=code, message=message)

    def _status(self, **fields: Any) -> None:
        """
        Merge fields into the unpack status, and tell the reporter if any. Only reports,
        never changes the unpacking. Never raises.
        """
        if self.status_reporter is None:
            return
        self._status_fields.update(fields)
        try:
            self.status_reporter(dict(self._status_fields))
        except Exception as e:
            logger.error("Could not report unpack status: %s", e)

    def _status_entries_done(self, done: int, total: int) -> None:
        # 100 only once published
        percent = min(99, 100 * done // total) if total else 0
        self._status(entries_done=done, percent=percent)

    def _report(self, parent: Path, file_name: str, text: str) -> None:
        """
        If in background, write text, with {when} replaced, into the error file for file_name.
        Never raises.
        """
        if not self.report_to_file:
            return
        try:
            when = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self._error_file(parent, file_name).write_text(text.replace("{when}", when))
        except Exception as e2:
            logger.error("Could not report unpack failure of %s: %s", file_name, e2)

    @staticmethod
    def _is_tar(filepath: str) -> bool:
        """tarfile.is_tarfile, but also False when the content is a corrupt compressed stream"""
        try:
            return tarfile.is_tarfile(filepath)
        except (EOFError, zlib.error, gzip.BadGzipFile):
            return False

    @staticmethod
    def _is_gz(filepath: str) -> bool:
        with open(filepath, "rb") as f:
            signature = f.read(2)
        return signature == b"\x1f\x8b"

    @classmethod
    def is_compressed(cls, path: Path) -> bool:
        posix_path = path.as_posix()
        return (
            zipfile.is_zipfile(posix_path)
            or cls._is_tar(posix_path)
            or cls._is_gz(posix_path)
        )

    def dispatch_unpack(self, compressed_path: Path, to_path: Path) -> None:
        """
        Top-level unpacking of compressed_path, an uploaded file, into to_path.
        All or nothing for an archive: it is extracted, recursively, into a private
        staging directory, which content is moved into to_path only on success.
        On failure, the staging directory (archive and partial output) is removed.
        """
        archive_name = compressed_path.name
        self._reset_unpack_budget()
        self._status_fields = {}
        if not self.is_compressed(compressed_path):
            self._dispatch_nested(compressed_path, to_path)
            if not compressed_path.exists():
                # Removed by the format check
                e = FileTypeRefusedException()
                self._report_failure(to_path, archive_name, e)
                raise e
            self._status(
                state="done",
                name=archive_name,
                percent=100,
                result_paths=self._relative_paths(to_path, [archive_name]),
            )
            self._error_file(to_path, archive_name).unlink(missing_ok=True)
            return
        self._status(state="unpacking", name=archive_name, percent=0)
        staging = self._new_staging_dir(to_path, compressed_path)
        # If this process dies meanwhile, the next one to start cleans up
        with registered(
            self.registry_dir,
            {
                "staging": str(staging.absolute()),
                "parent": str(to_path.absolute()),
                "name": archive_name,
                "user_id": self.user_id,
                "upload_id": self.upload_id,
            },
        ):
            try:
                try:
                    relative = compressed_path.relative_to(to_path)
                except ValueError:
                    relative = Path(archive_name)
                # Same relative position, so the same layout as without staging
                staged_archive = staging / relative
                staged_archive.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(compressed_path, staged_archive)
                self._dispatch_nested(staged_archive, staging)
                published = self._publish(staging, to_path)
            except Exception as e:
                shutil.rmtree(staging, ignore_errors=True)
                compressed_path.unlink(missing_ok=True)
                self._report_failure(to_path, archive_name, e)
                raise
        self._status(
            state="done",
            percent=100,
            result_paths=self._relative_paths(to_path, published),
        )
        # A previous failure of the same archive is not relevant anymore
        self._error_file(to_path, archive_name).unlink(missing_ok=True)

    def _relative_paths(self, parent: Path, names: List[str]) -> List[str]:
        """Paths of names in parent, relative to the user root, as My Files shows them"""
        ret = []
        for a_name in names:
            try:
                if self._root_path is not None:
                    ret.append(
                        (parent / a_name)
                        .absolute()
                        .relative_to(self._root_path.absolute())
                        .as_posix()
                    )
                else:
                    ret.append(a_name)
            except ValueError:
                ret.append(a_name)
        return ret

    def _dispatch_nested(self, compressed_path: Path, to_path: Path) -> None:
        if zipfile.is_zipfile(compressed_path.as_posix()):
            with self._one_level_deeper():
                self.unpack_zip(compressed_path, to_path)
        elif self._is_tar(compressed_path.as_posix()):
            with self._one_level_deeper():
                self.unpack_tar(compressed_path, to_path)
        elif self._is_gz(compressed_path.as_posix()):
            with self._one_level_deeper():
                self.unpack_gz(compressed_path, to_path)
        elif not self._has_accepted_format(to_path, str(compressed_path)):
            os.remove(compressed_path)
            self.list_errors.update({"Not accepted": str(compressed_path)})
        logger.info(f"Unpack done for {compressed_path}->{to_path}")


@contextlib.contextmanager
def registered(
    registry_dir: Optional[Path], info: Dict[str, Any]
) -> Generator[None, None, None]:
    """
    Register, while in the block, an unpacking described by info (staging, parent, name,
    user_id, upload_id). Best effort: a registry problem never prevents the unpacking.
    """
    entry: Optional[Path] = None
    fd: Optional[int] = None
    if registry_dir is not None:
        tmp_name = None
        try:
            registry_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=registry_dir, suffix=TMP_SUFFIX)
            fcntl.flock(fd, fcntl.LOCK_EX)
            data = dict(info, pid=os.getpid(), started=_now())
            os.write(fd, json.dumps(data).encode("utf-8"))
            # Published locked and complete, the lock follows the inode
            entry = registry_dir / (uuid.uuid4().hex + SUFFIX)
            os.replace(tmp_name, entry)
            _LIVE.add(str(entry))
        except Exception as e:
            logger.error("Could not register unpacking %s: %s", info, e)
            if tmp_name is not None:
                Path(tmp_name).unlink(missing_ok=True)
            if fd is not None:
                os.close(fd)
            fd, entry = None, None
    try:
        yield
    finally:
        if entry is not None:
            entry.unlink(missing_ok=True)
            _LIVE.discard(str(entry))
        if fd is not None:
            os.close(fd)


def sweep_stale(registry_dir: Path, users_files_dir: Path) -> int:
    """
    Clean up after the unpackings of dead processes: remove their staging folder, tell the
    user in an error file and in the upload status. Return the number of entries cleaned.
    Never raises for one entry.
    """
    if not registry_dir.is_dir():
        return 0
    ret = 0
    for an_entry in sorted(registry_dir.iterdir()):
        if str(an_entry) in _LIVE:
            continue
        if an_entry.name.endswith(TMP_SUFFIX):
            try:
                if time.time() - an_entry.stat().st_mtime < TMP_GRACE:
                    continue
            except OSError:
                continue
        elif not an_entry.name.endswith(SUFFIX):
            continue
        try:
            if _sweep_one(an_entry, users_files_dir):
                ret += 1
        except Exception as e:
            logger.error("Could not sweep unpack entry %s: %s", an_entry, e)
    return ret


def _sweep_one(entry: Path, users_files_dir: Path) -> bool:
    try:
        fd = os.open(entry, os.O_RDWR)
    except FileNotFoundError:
        return False  # Done meanwhile
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False  # Live
        if not entry.exists():
            return False  # Done, or swept by another process, meanwhile
        if entry.name.endswith(TMP_SUFFIX):
            entry.unlink(missing_ok=True)
            return False
        try:
            info = json.loads(entry.read_text())
        except ValueError:
            info = None
        if isinstance(info, dict):
            _clean_up(info, users_files_dir)
        else:
            logger.error("Unreadable unpack entry %s, dropped", entry)
        entry.unlink(missing_ok=True)
        return True
    finally:
        os.close(fd)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _clean_up(info: Dict[str, Any], users_files_dir: Path) -> None:
    """The unpacking described by info was interrupted, undo and report it"""
    name = str(info.get("name", "?"))
    staging = Path(str(info.get("staging", "")))
    parent = Path(str(info.get("parent", "")))
    logger.warning(
        "Unpacking of %s by process %s was interrupted", info, info.get("pid")
    )
    # Never trust the path blindly
    if staging.name.startswith(PROGRESS_PREFIX) and _inside(staging, users_files_dir):
        shutil.rmtree(staging, ignore_errors=True)
    else:
        logger.error("Not removing unexpected staging path %s", staging)
    message = "Extraction of '%s' failed, nothing was kept: %s" % (
        name,
        DETAIL_UNPACK_INTERRUPTED,
    )
    if parent.is_dir() and _inside(parent, users_files_dir):
        when = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        try:
            Unpacker._error_file(parent, name).write_text(
                "%s UTC %s\n" % (when, message)
            )
        except OSError as e:
            logger.error("Could not report interrupted unpack of %s: %s", name, e)
    upload_id = info.get("upload_id")
    if upload_id:
        try:
            UnpackStatus(str(upload_id), int(info.get("user_id", -1)), name).update(
                {
                    "state": "error",
                    "status_code": INTERRUPTED_STATUS_CODE,
                    "message": message,
                }
            )
        except Exception as e:
            logger.error(
                "Could not set status of interrupted unpack %s: %s", upload_id, e
            )


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
