# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os.path
import tempfile
from pathlib import Path
from typing import Any

from BO.User import UserIDT


class UserDirectory(object):
    """
        Base directory for storing user files. So far just a temp space.
    """

    def __init__(self, user_id: UserIDT):
        self.user_id = user_id

    def _user_suffix(self):
        return "." + str(self.user_id)

    async def add_file(self, name: str, stream: Any) -> str:
        """
            Add the byte stream as the file with name 'name' into self.
        """
        path: Path = Path(tempfile.mkdtemp(suffix=self._user_suffix()))
        dest_path = path.absolute().joinpath(name)
        with open(dest_path, "wb") as fout:
            buff = await stream.read(1024)
            while len(buff) != 0:
                fout.write(buff)
                buff = await stream.read(1024)
        return str(dest_path)

    def contains(self, path_str: str) -> bool:
        """
            Check if given file path was (very likely) produced here.
        """
        parts = path_str.split(os.path.sep)
        if len(parts) < 3:
            return False
        if parts[1] == tempfile.gettempprefix() and parts[2].endswith(self._user_suffix()):
            return True
        return False
