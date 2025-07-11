# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import gzip
import os
import shutil
import tarfile
import zipfile
import asyncio
from asyncio import FIRST_EXCEPTION

from magic_rs import from_path
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from starlette.datastructures import UploadFile
from BO.User import UserIDT
from FS.CommonDir import CommonFolder, DirEntryT
from helpers.AppConfig import Config
from helpers.DynamicLogs import get_logger
from helpers.CustomException import BaseAppException, UnprocessableEntityException
from helpers.httpexception import (
    DETAIL_INVALID_ZIP_FILE,
    DETAIL_INVALID_LARGE_ZIP_FILE,
    DETAIL_UNKNOWN_ERROR,
    DETAIL_NOTHING_DONE,
    DETAIL_FILE_PROTECTED,
    DETAIL_SAME_NAME_IN_TRASH,
)

logger = get_logger(__name__)

accepted_mime_types = [
    "application/zip",
    "application/gzip",
    "application/x-tar",
    "text/plain",
    "text/csv",
    "text/tab-separated-values",
    "image/jpeg",
    "image/png",
    "image/x-png",
    "image/tiff",
]


class AsyncException(Exception):
    def __init__(self, message, *args, **kwargs):
        self.message = message
        super(*args, **kwargs)

    def __str__(self):
        return self.message


class UserFilesDirectory(object):
    """
    Base directory for storing user files.
    """

    USER_DIR_PATTERN = "ecotaxa_user.%d"
    TRASH_DIRECTORY = "trash."
    COMPRESSED_PATTERN = "*"
    ARCHIVE_EXTENSIONS = ["zip", "tar", "gzip", "tar.gz", "tar.bz2", "tar.xz", "gz"]
    TSV = ".tsv"

    def __init__(self, user_id: UserIDT):
        users_files_dir = Config().get_users_files_dir()
        self.user_id = user_id
        self.list_errors: Dict[str, str] = {}
        self._root_path = Path(
            str(users_files_dir or ""), self.USER_DIR_PATTERN % self.user_id
        )
        self.TRASH_DIRECTORY += str(self.user_id)

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
        # Copy data from the stream into dest_path
        with open(source_path, "wb") as file:
            buff = await stream.read(1024)
            while len(buff) != 0:
                file.write(buff)  # type:ignore # Mypy is unaware of async read result
                buff = await stream.read(1024)
        if zipfile.is_zipfile(source_path.as_posix()):
            await self.unpack_zip(source_path, base_path.absolute())
        elif tarfile.is_tarfile(source_path.as_posix()):
            await self.unpack_tar(source_path, base_path.absolute())
        elif self._is_gz(source_path.as_posix()):
            name = name.replace(".gz", "")
            await self.unpack_gz(
                source_path, base_path.absolute().joinpath(name.lstrip(os.path.sep))
            )
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
    def _is_gz(filepath):
        with open(filepath, "rb") as f:
            b1 = f.read(1)
            b2 = f.read(1)
            f.close()
        return b1 == b"\x1f" and b2 == b"\x8b"

    def _is_trash_dir_throw(self, path: str):
        if self._root_path.joinpath(
            path.lstrip(os.path.sep)
        ) == self._root_path.joinpath(self.TRASH_DIRECTORY):
            raise UnprocessableEntityException(DETAIL_FILE_PROTECTED)

    def _is_trash_dir(self, path: str):
        return self._root_path.joinpath(
            path.lstrip(os.path.sep)
        ) == self._root_path.joinpath(self.TRASH_DIRECTORY)

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
        self._is_trash_dir_throw(path)
        source_path: Path = self._root_path.joinpath(path.lstrip(os.path.sep))
        # send to trash if not in trash
        if (
            path[0 : len(self.TRASH_DIRECTORY + os.path.sep)]
            != self.TRASH_DIRECTORY + os.path.sep
        ):
            if os.path.exists(
                self._root_path.joinpath(self.TRASH_DIRECTORY + os.path.sep + path)
            ):
                raise UnprocessableEntityException(DETAIL_SAME_NAME_IN_TRASH)
            else:
                try:
                    self.ensure_exists(self._root_path.joinpath(self.TRASH_DIRECTORY))
                    self.move(path, self.TRASH_DIRECTORY + os.path.sep + path)
                except Exception as e:
                    _log_exception_throw(e)

        elif source_path.is_dir():
            try:
                shutil.rmtree(source_path)
            except Exception as e:
                _log_exception_throw(e)
        else:
            try:
                os.remove(source_path)
            except Exception as e:
                _log_exception_throw(e)

    def create(self, path: str) -> str:
        self._is_trash_dir_throw(path[0 : len(self.TRASH_DIRECTORY + os.path.sep)])
        source_path: Path = self._root_path.joinpath(path.lstrip(os.path.sep))
        if source_path.exists():
            raise UnprocessableEntityException(DETAIL_NOTHING_DONE)
        self.ensure_exists(source_path)
        return str(source_path)

    def extract_archive(self, archive, path: Path):
        if hasattr(archive, "testzip"):
            archive.testzip()
        if hasattr(archive, "namelist"):
            filenames = archive.namelist()
        else:
            # tarfile
            filenames = archive.getnames()
        extracted = []
        archive.extractall(path)
        more_mime = {
            "csv": "text/csv",
            "txt": "text/plain",
            "tsv": "text/tab-separated-values",
        }
        for filename in filenames:
            file_ext, compressed_path, mime_type = self._get_file_info(filename, path)
            if mime_type in accepted_mime_types:
                extracted.append(filename)
            elif file_ext in more_mime.keys():
                extracted.append(filename)
            else:
                try:
                    os.remove(compressed_path)
                except Exception as e:
                    _log_exception_throw(e)
                logger.info("NOT EXTRACTED '%s' ", str(compressed_path))
        return extracted

    @staticmethod
    def _get_file_info(filename: str, path: Path) -> Tuple[str, Path, str]:
        file_ext = filename.split(".")[-1]
        parts = filename.split(os.path.sep)
        filepath = path.joinpath(str(Path(parts[0])), os.path.sep.join(parts[1:]))
        try:
            py_magic = from_path(str(filepath))
            mime_type = py_magic.mime_type()
        except Exception:
            mime_type = "none"

        return file_ext, filepath, mime_type

    @staticmethod
    def ensure_exists(path: Path):
        if not path.exists():
            try:
                path.mkdir(parents=True)
            except FileExistsError:
                pass

    def _has_accepted_format(self, path: Path, filename: str) -> bool:
        py_magic = from_path(filename)
        mime_type = py_magic.mime_type()
        if mime_type in accepted_mime_types:
            return True
        logger.info(
            "File format not accepted '%s' '%s' , user_id '%s'",
            path,
            filename,
            str(self.user_id),
        )
        path_error = str(path.joinpath(filename.lstrip(os.path.sep)))
        self.list_errors.update({"Not accepted": path_error})
        return False

    async def unpack_zip(self, input_path: Path, path: Path):
        compressed_file = input_path.as_posix()
        try:
            with zipfile.ZipFile(compressed_file, "r", allowZip64=True) as archive:
                filenames = self.extract_archive(archive, path)
            if len(filenames):
                await self.recursive_unpack(path, filenames)
            os.remove(compressed_file)
        except Exception as e:
            _log_exception_throw(e)

    async def unpack_tar(self, input_path: Path, path: Path):
        compressed_file = input_path.as_posix()
        try:
            with tarfile.open(compressed_file, "r") as archive:
                filenames = self.extract_archive(archive, path)
            if len(filenames):
                await self.recursive_unpack(path, filenames)
            os.remove(compressed_file)
        except Exception as e:
            _log_exception_throw(e)

    async def unpack_gz(self, input_path: Path, path: Path):
        compressed_file = input_path.as_posix()
        try:
            with open(compressed_file, "rb") as archive:
                with open(path.as_posix(), "wb") as decompressed_file:
                    decompressed_file.write(gzip.decompress(archive.read()))
            name = str(compressed_file).split(os.path.sep)[-1]
            await self.dispatch_unpack(name, path)
            os.remove(compressed_file)
        except Exception as e:
            _log_exception_throw(e)

    async def recursive_unpack(self, path: Path, filenames: List[str]):
        tasks = []
        for compressed_f in filenames:
            tasks.append(asyncio.create_task(self.dispatch_unpack(compressed_f, path)))
        done, pending = await asyncio.wait(tasks, return_when=FIRST_EXCEPTION)
        for p in pending:
            logger.error(p.result())

    async def dispatch_unpack(self, compressed_f: str, path: Path):
        file_ext, compressed_path, mime_type = self._get_file_info(compressed_f, path)
        if (
            file_ext in self.ARCHIVE_EXTENSIONS
            and not compressed_path.is_dir()
            and not self._is_trash_dir(str(path))
        ):
            sub_path = Path(".".join(str(compressed_path).split(".")[:-1]))
            if zipfile.is_zipfile(compressed_path.as_posix()):
                await self.unpack_zip(compressed_path, sub_path)
            elif tarfile.is_tarfile(compressed_path.as_posix()):
                await self.unpack_tar(compressed_path, sub_path)
            elif self._is_gz(compressed_path.as_posix()):
                await self.unpack_gz(compressed_path, sub_path)
            elif not self._has_accepted_format(sub_path, compressed_f):
                os.remove(compressed_path)
                self.list_errors.update({"Not accepted": compressed_f})


def _log_exception_throw(e: Exception):
    if isinstance(e, zipfile.BadZipFile):
        logger.error(DETAIL_INVALID_ZIP_FILE)
        raise UnprocessableEntityException(DETAIL_INVALID_ZIP_FILE) from e
    elif isinstance(e, zipfile.LargeZipFile):
        # activate zip64
        logger.error(DETAIL_INVALID_LARGE_ZIP_FILE)
        raise UnprocessableEntityException(DETAIL_INVALID_LARGE_ZIP_FILE) from e
    else:
        logger.error(DETAIL_UNKNOWN_ERROR)
        raise BaseAppException(DETAIL_UNKNOWN_ERROR) from e
