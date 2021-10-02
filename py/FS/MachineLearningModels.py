# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os
from pathlib import Path
from typing import Any


class SavedModels(object):
    """
         The ML models are in memory during their building/usage, but they can be serialized.
         They also need temporary storage while they build.
    """
    MODELS_CONFIG_KEY = 'MODELSAREA'

    def __init__(self, config: Any):
        base_path = config[self.MODELS_CONFIG_KEY]
        base_path = base_path.strip("'")
        self.path: Path = Path(base_path)

    def get_checkpoints_dir(self, model_name: str) -> Path:
        # directory to save training checkpoints
        ckpt_dir = self.path / model_name / 'checkpoints'
        os.makedirs(ckpt_dir, exist_ok=True)
        return ckpt_dir

    def extractor_path(self, model_name: str) -> Path:
        # Used during CNN usage for generating
        return self.path / model_name / "extractor"

    def best_model_path(self, model_name: str) -> Path:
        return self.path / model_name / "best_model"

    def reducer_pickle_path(self, model_name: str) -> Path:
        return self.path / model_name / "dim_reducer.pickle"
