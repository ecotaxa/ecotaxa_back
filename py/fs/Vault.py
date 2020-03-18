# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path, PurePath


class Vault(object):
    """
         Class mirroring the image vault (filesystem)
    """

    def __init__(self, path: str):
        self.path: Path = Path(path)
        self.ok_subs = set()

    def ensure_exists(self, sub_directory: str):
        """
            Ensure the sub-directory exists, i.e. create it, if not there.
            If another process asked for the same simultaneously then use it.
        :param sub_directory:
        """
        if sub_directory in self.ok_subs:
            return
        subdir: Path = self.path.joinpath(sub_directory)
        try:
            if not subdir.exists():
                subdir.mkdir()
        except Exception as e:
            if not subdir.exists():
                raise e
        self.ok_subs.add(sub_directory)

    def sub_path(self, sub_directory: str) -> PurePath:
        """
            Return a path to subdirectory of self.
        :return:
        """
        return self.path.joinpath(sub_directory)
