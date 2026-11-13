# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os
import shutil
from pathlib import Path
from typing import List, Optional

from starlette.datastructures import UploadFile

from DB.User import UserIDT
from FS import Unpack
from FS.CommonDir import CommonFolder, DirEntryT
from FS.Unpack import Unpacker, _log_exception_throw, get_tus_files_dir
from helpers.AppConfig import Config
from helpers.CustomException import UnprocessableEntityException
from helpers.httpexception import DETAIL_FILE_PROTECTED, DETAIL_NOTHING_DONE

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
        self.user_id = user_id
        self._root_path = Path(users_files_dir, self.USER_DIR_PATTERN % user_id)
        self.trash_directory = self.TRASH_DIRECTORY % user_id
        self.unpacker = Unpacker(
            root_path=self._root_path,
            user_id=user_id,
            list_errors={},
            registry_dir=get_unpack_registry_dir(),
        )

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
        _, compressed_path, _ = Unpacker.get_file_info(
            name.lstrip(os.path.sep), base_path.absolute()
        )
        self.unpacker.compressed_origin = compressed_path
        self.unpacker.dispatch_unpack(compressed_path, base_path.absolute())
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

    def _is_trash_dir_throw(self, path: str):
        if self._is_trash_dir(path):
            raise UnprocessableEntityException(DETAIL_FILE_PROTECTED)

    def _is_trash_dir(self, path: str) -> bool:
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

    @staticmethod
    def ensure_exists(path: Path):
        if not path.exists():
            try:
                path.mkdir(parents=True)
            except FileExistsError:
                pass


def get_unpack_registry_dir() -> Path:
    """Where unpackings in progress are registered, shared by all server processes."""
    return Path(get_tus_files_dir(), ".unpacking")


def sweep_stale_unpacks() -> int:
    """Clean up after the unpackings of dead processes, see Unpack."""
    return Unpack.sweep_stale(
        get_unpack_registry_dir(), Path(Config().get_users_files_dir())
    )
