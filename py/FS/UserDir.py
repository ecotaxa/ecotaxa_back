# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os.path
import tempfile
from pathlib import Path
from typing import Any, Optional, List, Set

from BO.User import UserIDT
from FS.CommonDir import CommonFolder, DirEntryT
from FS.TempDirForTasks import TempDirForTasks


class UserDirectory(object):
    """
    Base directory for storing user files. So far just a temp space.
    """

    USER_DIR_PATTERN = "ecotaxa_user.%d"
    user_dir_cache: Set[Path] = set()

    def __init__(self, user_id: UserIDT, tag: Optional[str] = None):
        self.user_id = user_id
        self.tag = tag

    def _user_suffix(self):
        return "." + str(self.user_id)

    async def add_file(self, name: str, path: Optional[str], stream: Any) -> str:
        """
        Add the byte stream as the file with name 'name' into self.
        :param name: File name.
        :param path: The client-side full path of the file. For replicating a directory structure.
        :param stream: The byte stream with file content.
        """
        base_path: Path
        if self.tag is not None:
            base_path = Path(
                tempfile.gettempdir(), self.USER_DIR_PATTERN % self.user_id
            )
            TempDirForTasks.ensure_exists(base_path, self.user_dir_cache)
            base_path /= self.tag
        else:
            base_path = Path(tempfile.mkdtemp(suffix=self._user_suffix()))
        if path is not None:
            assert path.endswith(name)
            base_path /= path[: -len(name)]
        TempDirForTasks.ensure_exists(base_path, self.user_dir_cache)
        dest_path = base_path.absolute().joinpath(name)

        # Copy data from the stream into dest_path
        with open(dest_path, "wb") as fout:
            buff = await stream.read(1024)
            while len(buff) != 0:
                fout.write(buff)
                buff = await stream.read(1024)
        return str(dest_path)

    def list(self, sub_path: str) -> List[DirEntryT]:
        """
        Only list the known (with tags) directory.
        """
        # Leading / implies root directory
        sub_path = sub_path.lstrip("/")
        ret: List[DirEntryT] = []
        path: Path = Path(
            tempfile.gettempdir(), self.USER_DIR_PATTERN % self.user_id, sub_path
        )
        CommonFolder.list_dir_into(path, ret)
        return ret

    def contains(self, path_str: str) -> bool:
        """
        Check if given file path was (very likely) produced here.
        """
        parts = path_str.split(os.path.sep)
        if len(parts) < 3:
            return False
        if parts[1] == tempfile.gettempprefix() and parts[2].endswith(
                self._user_suffix()
        ):
            return True
        return False
