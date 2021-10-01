# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path
from typing import Set


class SavedModels(object):
    """
         The ML models are in memory during their building/usage, but they can be serialized.
    """

    def __init__(self, path: str):
        self.path: Path = Path(path)
        self.ok_subs: Set[str] = set()

