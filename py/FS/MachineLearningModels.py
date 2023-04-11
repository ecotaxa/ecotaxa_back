# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os
from pathlib import Path
from typing import Any, List


class SavedModels(object):
    """
    The ML models are in memory during their building/usage, but they can be serialized.
    They also need temporary storage while they build.
    """

    MODELS_CONFIG_KEY = "MODELSAREA"
    PRFX = "io_"
    DIM_REDUCER_FILE = "dim_reducer.pickle"
    CROP_FILE = "crop.txt"
    FEATURE_EXTRACTOR_DIR = "feature_extractor"

    def __init__(self, config: Any):
        base_path = config.get_cnf(self.MODELS_CONFIG_KEY)
        base_path = base_path.strip("'")
        self.path: Path = Path(base_path)

    def list(self) -> List[str]:
        """
        Enumerate all the possibly usable models in self.
        """
        ret = []
        if self.path.exists():
            for a_dir in self.path.glob("*"):
                if not a_dir.is_dir():
                    continue
                if not (a_dir / self.DIM_REDUCER_FILE).is_file():
                    continue
                if not (a_dir / self.CROP_FILE).is_file():
                    continue
                if not (a_dir / self.FEATURE_EXTRACTOR_DIR).is_dir():
                    continue
                dir_name = a_dir.name
                if not dir_name.startswith(self.PRFX):
                    continue
                dir_name = dir_name[len(self.PRFX) :]
                ret.append(dir_name)
        return ret

    def _prefix(self, name: str) -> str:
        return self.PRFX + name

    def get_checkpoints_dir(self, model_name: str) -> Path:
        # Directory to save training checkpoints
        # Used during training only
        model_name = self._prefix(model_name)
        ckpt_dir = self.path / model_name / "checkpoints"
        os.makedirs(ckpt_dir, exist_ok=True)
        return ckpt_dir

    def best_model_path(self, model_name: str) -> Path:
        # Used during training only
        model_name = self._prefix(model_name)
        return self.path / model_name / "best_model"

    def extractor_path(self, model_name: str) -> Path:
        # Used during both training and extraction
        model_name = self._prefix(model_name)
        return self.path / model_name / self.FEATURE_EXTRACTOR_DIR

    def reducer_pickle_path(self, model_name: str) -> Path:
        # Used during both training and extraction
        model_name = self._prefix(model_name)
        return self.path / model_name / self.DIM_REDUCER_FILE

    def crop_values_path(self, model_name: str) -> Path:
        # Used during both training and extraction
        model_name = self._prefix(model_name)
        return self.path / model_name / self.CROP_FILE
