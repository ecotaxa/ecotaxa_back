# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path
from typing import Any


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
        return self.path.joinpath(sub_path).as_posix()
