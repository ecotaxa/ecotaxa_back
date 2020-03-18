# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

import pathlib


def create_dir_concurrently_if_needed(dir_path: pathlib.Path):
    """
    Create the wanted directory, if it does not exist.
    In case the creation fails, consider it's OK if it already exists.
    :param dir_path: directory to create
    """
    try:
        if not dir_path.exists():
            dir_path.mkdir()
    except Exception as e:
        if not dir_path.exists():
            raise e
