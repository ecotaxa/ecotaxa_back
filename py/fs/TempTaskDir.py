# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path


class TempTaskDir(object):
    """
        A directory for storing data for a task.
    """

    def __init__(self, path: str):
        self.path: Path = Path(path)

    def base_dir_for(self, task_id: int) -> Path:
        task_subdir = "task%06d" % task_id
        ret = self.path.joinpath(task_subdir)
        if not ret.exists():
            # TODO: Cache for current instance
            ret.mkdir()
        return ret

    def data_dir_for(self, task_id: int) -> str:
        data_subdir = self.base_dir_for(task_id).joinpath("data")
        if not data_subdir.exists():
            # TODO: Cache for current instance
            data_subdir.mkdir()
        return str(data_subdir.absolute())
