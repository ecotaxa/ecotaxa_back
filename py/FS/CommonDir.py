# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from pathlib import Path
from typing import Any, List, Tuple


class CommonFolder(object):
    """
         The directory where files can be read by everyone.
         Pointed at by a configuration variable.
    """
    COMMON_FOLDER_CONFIG_KEY = 'SERVERLOADAREA'

    def __init__(self, config: Any):
        base_path = config[self.COMMON_FOLDER_CONFIG_KEY]
        base_path = base_path.strip("'")
        self.path: Path = Path(base_path)

    def path_to(self, sub_path: str) -> str:
        """
            Return absolute path to given relative subpath.
        :return:
        """
        # Leading / implies root directory
        sub_path = sub_path.lstrip("/")
        return self.path.joinpath(sub_path).as_posix()

    def list(self, sub_path: str) -> List[Tuple[str, str, int, str]]:
        """
            List given sub-path, returning the name of entries and details of zip files.
        """
        ret = []
        # Leading / implies root directory
        sub_path = sub_path.lstrip("/")
        abs_path = Path(self.path.joinpath(sub_path))
        for an_entry in abs_path.iterdir():
            if an_entry.is_dir():
                e_type = 'D'
            elif an_entry.is_file():
                e_type = 'F'
            else:
                continue
            entry_sz = 0
            str_entry_time = ""
            if an_entry.suffix.lower() == ".zip":
                entry_stat = an_entry.lstat()
                entry_sz = entry_stat.st_size
                entry_time = datetime.datetime.fromtimestamp(entry_stat.st_mtime)
                str_entry_time = entry_time.isoformat(" ")
            ret.append((an_entry.name, e_type, entry_sz, str_entry_time))
        return ret
