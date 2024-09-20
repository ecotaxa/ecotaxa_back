# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import shutil
from pathlib import Path
from typing import Optional, Set


class TempDirForTasks(object):
    """
    Base directory for storing data for all BG operations AKA Jobs.
    """

    def __init__(self, path: str):
        self.path: Path = Path(path)

    def base_dir_for(self, task_id: int) -> Path:
        task_subdir = "task%06d" % task_id
        ret = self.path.joinpath(task_subdir)
        self.ensure_exists(ret)
        return ret

    def data_dir_for(self, task_id: int) -> str:
        data_subdir = self.base_dir_for(task_id).joinpath("data")
        self.ensure_exists(data_subdir)
        return str(data_subdir.absolute())

    def unzipped_dir_for(self, task_id: int) -> str:
        unzip_subdir = self.base_dir_for(task_id).joinpath("unzip")
        self.ensure_exists(unzip_subdir)
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
        Wipe entire temp directory for this job ID.
        """
        temp_for_job = self.base_dir_for(job_id)
        try:
            shutil.rmtree(temp_for_job)
        except (FileNotFoundError, PermissionError):
            pass

    def archive_for(self, job_id: int, keep: Set[str]):
        """
        Leave only the 'keep' files inside the temporary directory
        """
        temp_for_job = self.base_dir_for(job_id)
        for an_entry in temp_for_job.iterdir():
            try:
                if an_entry.name in keep:
                    continue
                if an_entry.is_dir():
                    shutil.rmtree(an_entry)
                else:
                    an_entry.unlink()
            except (FileNotFoundError, PermissionError):
                pass

    @staticmethod
    def ensure_exists(path: Path, cache: Optional[Set] = None) -> None:
        if cache is None:
            cache = (
                set()
            )  # No cache required, so create a set for the duration of the call
        elif path in cache:
            return
        if path.exists():
            cache.add(path)
            return
        try:
            # @see ecotaxa/ecotaxa_dev/issues/688 : Sometimes the creations are concurrent
            path.mkdir(parents=True)
            cache.add(path)
        except FileExistsError:
            pass
