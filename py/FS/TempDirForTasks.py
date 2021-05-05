# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import shutil
from os.path import join
from pathlib import Path


class TempDirForTasks(object):
    """
        Base directory for storing data for all API_operations.
    """
    SUBDIR = 'temptask'

    def __init__(self, base_path: str):
        path = join(base_path, self.SUBDIR)
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

    def unzipped_dir_for(self, task_id: int) -> str:
        unzip_subdir = self.base_dir_for(task_id).joinpath("unzip")
        if not unzip_subdir.exists():
            # TODO: Cache for current instance
            unzip_subdir.mkdir()
        return str(unzip_subdir.absolute())

    def in_base_dir_for(self, job_id: int, file_name: str) -> str:
        """
            Return full path to a file at root of temporary directory.
        :param job_id: The job ID this temporary directory belongs to.
        :param file_name: The file name.
        :return: str
        """
        file_in_dir = self.base_dir_for(job_id).joinpath(file_name)
        return str(file_in_dir.absolute())

    def erase_for(self, job_id: int):
        """
            Wipe any directory, which belongs to another job with same ID.
        """
        temp_for_job = self.base_dir_for(job_id)
        try:
            shutil.rmtree(temp_for_job)
        except (FileNotFoundError, PermissionError):
            pass
