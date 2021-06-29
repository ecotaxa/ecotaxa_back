# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
import shutil
from pathlib import Path
from typing import Any, List, Tuple

DirEntryT = Tuple[str, str, int, str]

class CommonFolder(object):
    """
         The directory where files can be read by everyone.
         Pointed at by a configuration variable.
    """
    COMMON_FOLDER_CONFIG_KEY = 'SERVERLOADAREA'
    # Contains a subdirectory of previous
    EXPORT_CONFIG_KEY = 'FTPEXPORTAREA'

    def __init__(self, config: Any):
        base_path = config[self.COMMON_FOLDER_CONFIG_KEY]
        base_path = base_path.strip("'")
        self.path: Path = Path(base_path)

    def path_to(self, sub_path: str) -> str:
        """
            Return absolute path to given relative subpath.
        """
        # Leading / implies root directory
        sub_path = sub_path.lstrip("/")
        return self.path.joinpath(sub_path).as_posix()

    def list(self, sub_path: str) -> List[DirEntryT]:
        """
            List given sub-path, returning the name of entries and details of zip files.
        """
        ret: List[DirEntryT] = []
        # Leading / implies root directory
        sub_path = sub_path.lstrip("/")
        abs_path = Path(self.path.joinpath(sub_path))
        return self.list_dir_into(abs_path, ret)

    @staticmethod
    def list_dir_into(abs_path, out):
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
            out.append((an_entry.name, e_type, entry_sz, str_entry_time))
        return out


class ExportFolder(object):
    """
         The directory where exports are produced, if asked so.
    """
    # Contains a subdirectory of previous
    EXPORT_CONFIG_KEY = 'FTPEXPORTAREA'

    def __init__(self, config: Any):
        base_path = config[self.EXPORT_CONFIG_KEY]
        base_path = base_path.strip("'")
        self.path: Path = Path(base_path)

    def receive_from(self, src_path: Path, as_name: str):
        """
            Copy a file into self, as :param as_name.
        """
        if not self.path.exists():
            self.path.mkdir()
        dst_file = self.path / as_name
        # fichier.rename(fichierdest) si ce sont des volumes sur des devices differents ça ne marche pas
        shutil.copyfile(src_path.as_posix(), dst_file.as_posix())
