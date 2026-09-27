# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import gzip
import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from magic_rs import from_path, CantMatchTypeError
from starlette.datastructures import UploadFile

from DB.User import UserIDT
from FS.CommonDir import CommonFolder, DirEntryT
from helpers.AppConfig import Config
from helpers.CustomException import UnprocessableEntityException
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_INVALID_ZIP_FILE,
    DETAIL_UNKNOWN_ERROR,
    DETAIL_NOTHING_DONE,
    DETAIL_FILE_PROTECTED,
)

logger = get_logger(__name__)
BUFFER_SIZE = 1024 * 1024


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
        self.archive_extensions: List[str] = config.get_archive_extensions()
        self.user_id = user_id
        self.list_errors: Dict[str, str] = {}
        self._root_path = Path(users_files_dir, self.USER_DIR_PATTERN % self.user_id)
        self.trash_directory = self.TRASH_DIRECTORY % self.user_id
        self.compressed_origin: Optional[Path] = None

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
        file_ext, compressed_path, mime_type = self._get_file_info(
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
            _log_exception_throw(e)
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
                _log_exception_throw(e)

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
            _log_exception_throw(e)

    def create(self, path: str) -> str:
        # Cannot create directly in trash
        self._is_trash_dir_throw(path[0 : len(self.trash_directory + os.path.sep)])
        source_path: Path = self._root_path.joinpath(path.lstrip(os.path.sep))
        if source_path.exists():
            raise UnprocessableEntityException(DETAIL_NOTHING_DONE)
        self.ensure_exists(source_path)
        return str(source_path)

    def extract_archive(self, archive, filepath: str, path: Path):
        if hasattr(archive, "namelist"):
            filenames = archive.namelist()
        else:
            # tarfile
            filenames = archive.getnames()
        extracted = []
        sub_path = filepath[len(str(path)) :]
        sub_path = ".".join(sub_path[1:].split(".")[:-1]) + os.path.sep
        if sub_path != "temp/" and (filenames[0][0 : len(sub_path)] != sub_path):
            path = path.joinpath(sub_path[:-1])
        archive.extractall(path.as_posix())
        more_mime = {
            "csv": "text/csv",
            "txt": "text/plain",
            "tsv": "text/tab-separated-values",
        }
        for filename in filenames:
            file_ext, compressed_path, mime_type = self._get_file_info(filename, path)
            if mime_type in self.accepted_mime_types:
                extracted.append(filename)
                if (
                    file_ext in self.archive_extensions
                    and not compressed_path.is_dir()
                    and not self._is_trash_dir(str(path))
                ):
                    self.dispatch_unpack(compressed_path, path)
            elif file_ext in more_mime.keys():
                extracted.append(filename)
            elif os.path.isdir(compressed_path):
                continue
            else:
                os.remove(compressed_path)
                logger.info("NOT EXTRACTED '%s' ", str(compressed_path))
        return sub_path

    @staticmethod
    def _get_file_info(filename: str, path: Path) -> Tuple[str, Path, Optional[str]]:
        file_ext = filename.split(".")[-1]
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
            _log_exception_throw(e, self.compressed_origin)
        finally:
            input_path.unlink(missing_ok=True)

    def unpack_tar(self, input_path: Path, path: Path) -> None:
        try:
            with tarfile.open(input_path, "r") as archive:
                self.extract_archive(archive, str(input_path), path)
        except Exception as e:
            _log_exception_throw(e, self.compressed_origin)
        finally:
            input_path.unlink(missing_ok=True)

    def unpack_gz(self, input_path: Path, path: Path) -> None:
        decompressed_path = input_path.with_suffix("")
        try:
            with gzip.open(input_path, "rb") as f_in, open(
                decompressed_path, "wb"
            ) as f_out:
                shutil.copyfileobj(f_in, f_out)
            self.dispatch_unpack(path / decompressed_path.name, path)
        except Exception as e:
            if decompressed_path.exists():
                decompressed_path.unlink()
            _log_exception_throw(e, self.compressed_origin)
        finally:
            input_path.unlink(missing_ok=True)

    def dispatch_unpack(self, compressed_path: Path, path: Path):
        if zipfile.is_zipfile(compressed_path.as_posix()):
            self.unpack_zip(compressed_path, path)
        elif tarfile.is_tarfile(compressed_path.as_posix()):
            self.unpack_tar(compressed_path, path)
        elif self._is_gz(compressed_path.as_posix()):
            self.unpack_gz(compressed_path, path)
        elif not self._has_accepted_format(path, str(compressed_path)):
            os.remove(compressed_path)
            self.list_errors.update({"Not accepted": str(compressed_path)})


def _log_exception_throw(e: Exception, path: Optional[Path] = None):
    if isinstance(e, zipfile.BadZipFile):
        message = DETAIL_INVALID_ZIP_FILE
        code = 422
    else:
        message = DETAIL_UNKNOWN_ERROR
        code = 500
    logger.error(str(code) + " " + message + " " + str(path))
    raise
