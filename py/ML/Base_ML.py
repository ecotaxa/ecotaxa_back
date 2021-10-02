# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# (c) 2021 Jean-Olivier Irisson, GNU General Public License v3
#

from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class MachineLearningBase(object):
    """
        Base class as many ML classes share the same data/behavior, which is to access EcoTaxa images/data,
        and produce data, either in FS or in memory.
    """

    def __init__(self, vault: Vault, model_dir: SavedModels):
        self.vault = vault
        self.model_dir = model_dir

    def full_img_paths(self, paths):
        """
            Prefix image paths to get the physical full path.
        """
        nb_loaded = 0
        for an_img in paths:
            nb_loaded += 0 if self.vault.ensure_there(an_img) else 1
        vault_def = self.vault.path_to
        if nb_loaded != len(paths):
            logger.info("Downloaded %d images", nb_loaded)
        return [vault_def(an_img) for an_img in paths]
