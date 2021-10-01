# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# (c) 2021 Jean-Olivier Irisson, GNU General Public License v3
#
import os
from pathlib import Path

from FS.Vault import Vault


class MachineLearningBase(object):
    """
        Base class as many ML classes share the same data/behavior, which is to access EcoTaxa images/data,
        and produce data, either in FS or in memory.
    """

    def __init__(self, vault: Vault, model_dir: Path):
        self.vault = vault
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    def full_img_paths(self, paths):
        """
            Prefix image paths to get the physical full path.
        """
        for an_img in paths:
            self.vault.ensure_there(an_img)
        vault_def = self.vault.path_to
        return [vault_def(an_img) for an_img in paths]

    def extractor_path(self) -> Path:
        return self.model_dir / "extractor"

    def best_model_path(self) -> Path:
        return self.model_dir / "best_model"

    def reducer_pickle_path(self) -> Path:
        return self.model_dir / "dim_reducer.pickle"