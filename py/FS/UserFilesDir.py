# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import contextlib
import datetime
import gzip
import os
import shutil
import tarfile
import zipfile
import zlib
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Generator

from magic_rs import from_path, CantMatchTypeError
from starlette.datastructures import UploadFile

from DB.User import UserIDT
from FS.CommonDir import CommonFolder, DirEntryT
from helpers.AppConfig import Config
from helpers.CustomException import UnprocessableEntityException, BaseAppException
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_CORRUPT_ARCHIVE,
    DETAIL_ARCHIVE_MEMBER_REFUSED,
    DETAIL_NOTHING_DONE,
    DETAIL_FILE_PROTECTED,
    DETAIL_EMPTY_ARCHIVE,
    DETAIL_UNPACK_TOO_LARGE,
    DETAIL_UNPACK_TOO_MANY_ENTRIES,
    DETAIL_UNPACK_TOO_DEEP,
    DETAIL_UNPACK_NO_DISK_SPACE,
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


class EmptyArchiveException(UnprocessableEntityException):
    """An archive without any entry"""

    def __init__(self) -> None:
        super().__init__(DETAIL_EMPTY_ARCHIVE)


class InsufficientStorageException(BaseAppException):
    """Not the user's fault, the server disk is (almost) full"""

    def __init__(self, message: str):
        super().__init__(message, status_code=507)


class UserFilesDirectory(object):
    """
    Base directory for storing user files.
    """

    USER_DIR_PATTERN = "ecotaxa_user.%d"
    TRASH_DIRECTORY = "trash.%d"
    COMPRESSED_PATTERN = "*"
    TSV = ".tsv"

    def __init__(self, user_id: UserIDT):
        config = Config()
        users_files_dir = config.get_users_files_dir()
        self.accepted_mime_types: List[str] = config.get_accepted_mime_types()
        self.archive_extensions: List[str] = [
            an_ext.lower() for an_ext in config.get_archive_extensions()
        ]
        self.user_id = user_id
        self.list_errors: Dict[str, str] = {}
        self._root_path = Path(users_files_dir, self.USER_DIR_PATTERN % self.user_id)
        self.trash_directory = self.TRASH_DIRECTORY % self.user_id
        self.compressed_origin: Optional[Path] = None
        # When set, an unpack failure is reported in a file next to the archive
        self.report_to_file = False
        # Limits of one upload once unpacked, nested archives included
        self.max_unpacked_size = config.get_max_unpacked_size()
        self.max_unpack_depth = config.get_max_unpack_depth()
        self.max_unpack_entries = config.get_max_unpack_entries()
        self.min_free_disk_ratio, self.min_free_disk_bytes = (
            config.get_unpack_min_free_disk()
        )
        self._reset_unpack_budget()

    def switch_to_background(self):
        """Future unpacking operations run in background, nobody gets their exceptions,
        so report failures to the user in an error file."""
        self.report_to_file = True

    async def add_file(self, name: str, path: Optional[str], stream: UploadFile) -> str:
        """
        Add the byte stream as the file with name 'name' into self.
        :param name: File name.
        :param path: The client-side full path of the file. For replicating a directory structure.
        :param stream: The byte stream with file content.
        """
        base_path: Path = self._root_path
        self.ensure_exists(base_path)
        if path is not None:
            assert path.endswith(name)
            base_path /= path[: -len(name)]
            self.ensure_exists(base_path)
        source_path = base_path.absolute().joinpath(name.lstrip(os.path.sep))
        # Copy data from the stream into source_path
        with open(source_path, "wb") as file:
            buff = await stream.read(BUFFER_SIZE)
            while len(buff) != 0:
                file.write(buff)  # type: ignore # Mypy is unaware of async read result
                buff = await stream.read(BUFFER_SIZE)
        _, compressed_path, _ = self._get_file_info(
            name.lstrip(os.path.sep), base_path.absolute()
        )
        self.compressed_origin = compressed_path
        self.dispatch_unpack(compressed_path, base_path.absolute())
        return str(source_path)

    def list(self, sub_path: str) -> List[DirEntryT]:
        """
        Only list the known (with tags) directory.
        """
        # Leading / implies root directory
        self.ensure_exists(self._root_path)
        sub_path = sub_path.lstrip(os.path.sep)
        ret: List[DirEntryT] = []
        path: Path = self._root_path.joinpath(sub_path)

        CommonFolder.list_dir_into(path, ret)
        return ret

    @staticmethod
    def _is_gz(filepath: str) -> bool:
        with open(filepath, "rb") as f:
            signature = f.read(2)
        return signature == b"\x1f\x8b"

    def _is_trash_dir_throw(self, path: str):
        if self._is_trash_dir(path):
            raise UnprocessableEntityException(DETAIL_FILE_PROTECTED)

    def _is_trash_dir(self, path: str):
        return self._root_path.joinpath(
            path.lstrip(os.path.sep)
        ) == self._root_path.joinpath(self.trash_directory)

    def move(self, source_name: str, dest_name: str) -> str:
        self._is_trash_dir_throw(source_name)
        self._is_trash_dir_throw(dest_name)
        source_path: Path = self._root_path.joinpath(source_name.lstrip(os.path.sep))
        dest_path: Path = self._root_path.joinpath(dest_name.lstrip(os.path.sep))
        self.ensure_exists(dest_path.parent)
        if dest_path.is_dir():
            if dest_path.joinpath(source_path.stem).exists():
                raise UnprocessableEntityException(DETAIL_NOTHING_DONE)
        elif dest_path.exists():
            # can't rename
            raise UnprocessableEntityException(DETAIL_NOTHING_DONE)
        try:
            shutil.move(str(source_path), dest_path)
        except Exception as e:
            _log_exception_throw(e, f"moving {source_path} to {dest_path}")
        return str(dest_path)

    def remove(self, path: str):
        if path == "*" or self._is_trash_dir(str(path)):
            if path == "*":
                pathtoremove = self._root_path
                path = ""
            else:
                pathtoremove = self._root_path.joinpath(path)
                path += os.path.sep
            for item in os.listdir(pathtoremove):
                if (
                    pathtoremove.joinpath(item).is_file()
                    or item != self.trash_directory
                ):
                    self.remove(path + item)
            return
        self._is_trash_dir_throw(path)
        source_path: Path = self._root_path.joinpath(path.lstrip(os.path.sep))
        # send to trash if not in trash
        if not path.startswith(self.trash_directory + os.path.sep):
            trash_path = self._root_path.joinpath(self.trash_directory, path)
            if os.path.exists(trash_path):
                # raise UnprocessableEntityException(DETAIL_SAME_NAME_IN_TRASH)
                self._remove_definitely(trash_path)
            try:
                self.ensure_exists(self._root_path.joinpath(self.trash_directory))
                self.move(path, self.trash_directory + os.path.sep + path)
            except Exception as e:
                _log_exception_throw(e, f"trashing {path}")

        else:
            self._remove_definitely(source_path)

    @staticmethod
    def _remove_definitely(source_path: Path):
        try:
            if source_path.is_dir():
                shutil.rmtree(source_path)
            else:
                os.remove(source_path)
        except Exception as e:
            _log_exception_throw(e, f"removing definitely {source_path}")

    def create(self, path: str) -> str:
        # Cannot create directly in trash
        self._is_trash_dir_throw(path[0 : len(self.trash_directory + os.path.sep)])
        source_path: Path = self._root_path.joinpath(path.lstrip(os.path.sep))
        if source_path.exists():
            raise UnprocessableEntityException(DETAIL_NOTHING_DONE)
        self.ensure_exists(source_path)
        return str(source_path)

    def extract_archive(
        self, archive: zipfile.ZipFile | tarfile.TarFile, filepath: str, path: Path
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
        extracted = []

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

        # Validate extracted files, unpack nested archives, and purge unaccepted formats
        for filename in filenames:
            file_ext, compressed_path, mime_type = self._get_file_info(filename, path)

            # Recursively unpack nested archives (e.g., zip inside tar), of configured
            # archive types, even if their MIME type is not listed (e.g. .tar.bz2)
            if self._is_nested_archive(filename, compressed_path) and not self._is_trash_dir(
                str(path)
            ):
                extracted.append(filename)
                try:
                    self._dispatch_nested(compressed_path, path)
                except EmptyArchiveException:
                    # Nothing to keep from it, and it was removed. Not worth failing the whole upload.
                    logger.info("Empty nested archive '%s' removed", compressed_path)
            # Check if file matches configured accepted MIME types
            elif mime_type in self.accepted_mime_types:
                extracted.append(filename)
            # Accept text/tabular data files based on extension fallback
            elif file_ext in TEXT_EXTENSIONS:
                extracted.append(filename)
            # Preserve directory hierarchy
            elif os.path.isdir(compressed_path):
                continue
            # Remove unsupported or unaccepted files to prevent clutter and security risks
            else:
                os.remove(compressed_path)
                logger.info("NOT EXTRACTED '%s' ", str(compressed_path))

    def _is_nested_archive(self, filename: str, filepath: Path) -> bool:
        """
        Is the archive member an archive to unpack: its extension, possibly compound like
        "tar.gz" ("tgz" being "tar.gz"), is a configured archive one, and its content is an archive.
        """
        parts = filename.lower().rsplit("/", 1)[-1].split(".")
        if len(parts) < 2:
            return False
        candidates = {parts[-1]}
        if len(parts) >= 3:
            candidates.add(parts[-2] + "." + parts[-1])
        if parts[-1] == "tgz":
            candidates.add("tar.gz")
        if not candidates & set(self.archive_extensions):
            return False
        if filepath.is_dir():
            return False
        return self.is_compressed(filepath)

    @staticmethod
    def _get_file_info(filename: str, path: Path) -> Tuple[str, Path, Optional[str]]:
        # Lowercase, extensions are compared case-insensitively
        file_ext = filename.split(".")[-1].lower()
        parts = filename.split(os.path.sep)
        filepath = path.joinpath(str(Path(parts[0])), os.path.sep.join(parts[1:]))
        try:
            py_magic = from_path(str(filepath))
            mime_type = py_magic.mime_type()
        except (CantMatchTypeError, Exception):
            mime_type = None

        return file_ext, filepath, mime_type

    @staticmethod
    def ensure_exists(path: Path):
        if not path.exists():
            try:
                path.mkdir(parents=True)
            except FileExistsError:
                pass

    def _has_accepted_format(self, path: Path, filepath: str) -> bool:

        try:
            py_magic = from_path(filepath)
            mime_type = py_magic.mime_type()
        except (CantMatchTypeError, Exception):
            mime_type = None
        if mime_type in self.accepted_mime_types:
            return True
        # Same extension fallback as for archive members
        if filepath.split(".")[-1].lower() in TEXT_EXTENSIONS:
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
            with zipfile.ZipFile(input_path, "r", allowZip64=True) as archive:
                self.extract_archive(archive, str(input_path), path)
        except Exception as e:
            _unpack_exception_throw(e, str(self.compressed_origin))
        finally:
            input_path.unlink(missing_ok=True)

    def unpack_tar(self, input_path: Path, path: Path) -> None:
        try:
            with tarfile.open(input_path, "r") as archive:
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

    @contextlib.contextmanager
    def _one_level_deeper(self) -> Generator[None, None, None]:
        self._unpack_depth += 1
        try:
            if self._unpack_depth > self.max_unpack_depth:
                raise UnprocessableEntityException(
                    "%s (max. %d levels)" % (DETAIL_UNPACK_TOO_DEEP, self.max_unpack_depth)
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
                "%s (max. %d)" % (DETAIL_UNPACK_TOO_MANY_ENTRIES, self.max_unpack_entries)
            )
        self._unpacked_size += size
        if 0 < self.max_unpacked_size < self._unpacked_size:
            raise UnprocessableEntityException(
                "%s (max. %d bytes)" % (DETAIL_UNPACK_TOO_LARGE, self.max_unpacked_size)
            )
        # A 0 margin means no check
        if size > 0 and (self.min_free_disk_ratio or self.min_free_disk_bytes):
            usage = shutil.disk_usage(where)
            if self.min_free_disk_ratio is not None:
                min_free = usage.total * self.min_free_disk_ratio
            else:
                min_free = self.min_free_disk_bytes or 0
            if usage.free - size < min_free:
                logger.error(
                    "Disk almost full, refusing to unpack %d bytes into %s", size, where
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
    def _publish(cls, staging: Path, parent: Path) -> None:
        """
        Move the content of the staging directory into parent, merging into existing directories.
        """
        for an_entry in list(staging.iterdir()):
            cls._move_merging(an_entry, parent / an_entry.name)
        staging.rmdir()

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

    ERROR_FILE_SUFFIX = ".unpack_error.txt"

    @classmethod
    def _error_file(cls, parent: Path, archive_name: str) -> Path:
        return parent / (archive_name + cls.ERROR_FILE_SUFFIX)

    def _report_failure(self, parent: Path, archive_name: str, e: Exception) -> None:
        """
        If in background, leave a file telling the user why the archive produced nothing.
        Never raises.
        """
        if isinstance(e, BaseAppException):
            message = e.message
        else:
            message = str(e) if str(e) else repr(e)
        # No server path in the message
        for a_root in (str(self._root_path.absolute()), str(self._root_path)):
            message = message.replace(a_root, "")
        self._report(
            parent,
            archive_name,
            "Extraction of '%s' failed at {when} UTC, nothing was kept from it.\n"
            "[%s] %s\n" % (archive_name, e.__class__.__name__, message),
        )

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
    def is_compressed(path: Path) -> bool:
        posix_path = path.as_posix()
        return (
            zipfile.is_zipfile(posix_path)
            or UserFilesDirectory._is_tar(posix_path)
            or UserFilesDirectory._is_gz(posix_path)
        )

    def dispatch_unpack(self, compressed_path: Path, to_path: Path) -> None:
        """
        Top-level unpacking of compressed_path, an uploaded file, into to_path.
        All or nothing for an archive: it is extracted, recursively, into a private
        staging directory, which content is moved into to_path only on success.
        On failure, the staging directory (archive and partial output) is removed.
        """
        if not self.is_compressed(compressed_path):
            self._dispatch_nested(compressed_path, to_path)
            if compressed_path.exists():
                self._error_file(to_path, compressed_path.name).unlink(missing_ok=True)
            else:
                # Removed by the format check
                self._report(
                    to_path,
                    compressed_path.name,
                    "Upload of '%s' refused at {when} UTC, its file type is not accepted.\n"
                    % compressed_path.name,
                )
            return
        archive_name = compressed_path.name
        self._reset_unpack_budget()
        staging = self._new_staging_dir(to_path, compressed_path)
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
            self._publish(staging, to_path)
        except Exception as e:
            shutil.rmtree(staging, ignore_errors=True)
            compressed_path.unlink(missing_ok=True)
            self._report_failure(to_path, archive_name, e)
            raise
        # A previous failure of the same archive is not relevant anymore
        self._error_file(to_path, archive_name).unlink(missing_ok=True)

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


# What a broken archive, sent by the user, raises while being read
CORRUPT_ARCHIVE_EXCEPTIONS = (
    zipfile.BadZipFile,
    zlib.error,
    tarfile.TarError,
    gzip.BadGzipFile,
    EOFError,
)


def _unpack_exception_throw(e: Exception, context: Optional[str] = None):
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


def _log_exception_throw(e: Exception, context: Optional[str] = None):
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
