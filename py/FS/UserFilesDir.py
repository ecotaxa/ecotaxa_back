# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os
import zipfile
import tarfile
import gzip
from glob import iglob
import shutil

# import magic
from pathlib import Path
from typing import Optional, List, Set, NamedTuple, Any, Dict
from helpers.DynamicLogs import get_logger
from starlette.datastructures import UploadFile
from BO.User import UserIDT
from FS.CommonDir import CommonFolder, DirEntryT
from helpers.AppConfig import Config
from fastapi import HTTPException
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
    "text/tab-separated-values",
    "image/jpeg",
    "image/png",
    "image/x-png",
    "image/tiff",
]


class DiskUsage(NamedTuple):
    total: int
    used: int
    free: int


class UserFilesDirectory(object):
    """
    Base directory for storing user files.
    """

    USER_DIR_PATTERN = "ecotaxa_user.%d"
    TRASH_DIRECTORY = "trash."
    COMPRESSED_PATTERN = "ecotaxa_*"
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
        # should always be zip but ...
        elif self._is_gz(source_path.as_posix()):
            name = name.replace(".gz", "")
            await self.unpack_gz(
                source_path, base_path.absolute().joinpath(name.lstrip(os.path.sep))
            )

        else:
            print("not zipped", str(source_path))
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
            raise HTTPException(status_code=422, detail=[DETAIL_FILE_PROTECTED])

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
                raise HTTPException(status_code=422, detail=DETAIL_NOTHING_DONE)
        elif dest_path.exists():
            # can't rename
            raise HTTPException(status_code=422, detail=DETAIL_NOTHING_DONE)
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
                raise HTTPException(
                    status_code=422,
                    detail=[DETAIL_SAME_NAME_IN_TRASH],
                )
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
            return ""
        self.ensure_exists(source_path)
        return str(source_path)

    def disk_usage(self, path: str) -> shutil._ntuple_diskusage:
        ospath = self._root_path.joinpath(path.lstrip(os.path.sep))
        return shutil.disk_usage(ospath)

    @staticmethod
    def ensure_exists(path: Path) -> None:
        if not path.exists():
            try:
                path.mkdir(parents=True)
            except FileExistsError:
                pass

    def _has_accepted_format(self, path: Path, filename: str) -> bool:
        mime_type = "application/zip"
        # mime = magic.Magic(mime=True)
        # mime_type = mime.from_file(file)
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

    async def unpack_only_zip(self, input_path: Path, path: Path):
        zip_file = input_path.as_posix()
        try:
            with zipfile.ZipFile(zip_file, "r", allowZip64=True) as archive:
                archive.extractall(path)
                for zip_f in iglob(str(path.joinpath("*/*.zip"))):
                    zip_path = Path(zip_f)
                    if not zip_path.is_dir():
                        if zipfile.is_zipfile(zip_path) == True:
                            sub_path = zip_path.parent
                            await self.unpack_only_zip(zip_path, sub_path)
                    elif not self._has_accepted_format(path, zip_f):
                        os.remove(zip_path)
                        self.list_errors.update({"Not accepted": zip_f})

            os.remove(zip_file)
        except Exception as e:
            _log_exception_throw(e)

    async def unpack_zip(self, input_path: Path, path: Path):
        compressed_file = input_path.as_posix()
        try:
            with zipfile.ZipFile(compressed_file, "r", allowZip64=True) as archive:
                archive.extractall(path)
            await self.unpack_archives(path)
            os.remove(compressed_file)
        except Exception as e:
            _log_exception_throw(e)

    async def unpack_tar(self, input_path: Path, path: Path):
        compressed_file = input_path.as_posix()
        try:
            with tarfile.open(compressed_file, "r") as archive:
                archive.extractall(path)
            await self.unpack_archives(path)
            os.remove(compressed_file)
        except Exception as e:
            _log_exception_throw(e)

    async def unpack_gz(self, input_path: Path, path: Path):
        compressed_file = input_path.as_posix()
        try:
            with open(compressed_file, "rb") as archive:
                with open(path.as_posix(), "wb") as decompressed_file:
                    decompressed_file.write(gzip.decompress(archive.read()))
            os.remove(compressed_file)
        except Exception as e:
            _log_exception_throw(e)

    async def unpack_archives(self, path: Path):
        try:
            for archive_ext in self.ARCHIVE_EXTENSIONS:
                await self.recursive_unpack(archive_ext, path)

        except Exception as e:
            _log_exception_throw(e)

    async def recursive_unpack(self, archive_ext: str, path: Path):
        for compressed_f in iglob(
            str(path.joinpath(self.COMPRESSED_PATTERN + "." + archive_ext))
        ):
            compressed_path = Path("**/" + compressed_f)
            if not compressed_path.is_dir() and not self._is_trash_dir(compressed_f):
                sub_path = compressed_path.parent
                if zipfile.is_zipfile(compressed_path):
                    await self.unpack_zip(compressed_path, sub_path)
                elif tarfile.is_tarfile(compressed_path):
                    await self.unpack_tar(compressed_path, sub_path)
                elif self._is_gz(compressed_path.as_posix()):
                    await self.unpack_gz(compressed_path, sub_path)
                elif not self._has_accepted_format(path, compressed_f):
                    os.remove(compressed_path)
                    self.list_errors.update({"Not accepted": compressed_f})


def _log_exception_throw(e: Exception):
    if isinstance(e, zipfile.BadZipFile):
        raise HTTPException(
            status_code=422,
            detail=[DETAIL_INVALID_ZIP_FILE],
        )
    elif isinstance(e, zipfile.LargeZipFile):
        # activate zip64
        raise HTTPException(
            status_code=422,
            detail=[DETAIL_INVALID_LARGE_ZIP_FILE],
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=[DETAIL_UNKNOWN_ERROR],
        )
