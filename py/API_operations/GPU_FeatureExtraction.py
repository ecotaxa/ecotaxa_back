# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Extract DeepFeatures on a project.
#
from typing import Dict, List, Tuple

import numpy as np

from BO.Prediction import DeepFeatures
from BO.Rights import RightsBO, Action
from DB.Project import ProjectIDT, Project
from ML.Deep_features_extractor import DeepFeaturesExtractor
from helpers.DynamicLogs import get_logger
from .helpers.JobService import JobServiceBase
from .FeatureExtraction import FeatureExtractionForProject
from helpers.Timer import CodeTimer

logger = get_logger(__name__)

# Remove job type for base class, so during run the flow ends here
FeatureExtractionForProject.JOB_TYPE = ""

class GPUFeatureExtractionForProject(FeatureExtractionForProject):
    """
    Part of the feature extraction which needs special HW and libs.
    """

    JOB_TYPE = "FeatureExtraction"

    DEEP_EXTRACT_CHUNK = 10000

    def ensure_deep_features_job(self) -> None:
        """
        Ensure that deep features are present for given project.
        """
        proj_id = self.prj_id
        model_name = self.prj.cnn_network_id
        
        msg = self._ensure_deep_features_for(proj_id, model_name)
        done_infos = {"message": msg}

        self.set_job_result(errors=[], infos=done_infos)
        return

    def _ensure_deep_features_for(self, proj_id: ProjectIDT, model_name: str) -> str:
        """
        Ensure that deep features are present for given project.
        """
        # Get data i.e objects ID and images from the project
        ids_and_images = DeepFeatures.find_missing(self.ro_session, proj_id)
        if len(ids_and_images) == 0:
            return "All CNN present for %d" % proj_id

        # Do reasonable chunks so we can see logs...
        nb_rows = 0
        extractor = DeepFeaturesExtractor(self.vault, self.models_dir)
        while len(ids_and_images) > 0:
            chunk = {}
            for objid, img in ids_and_images.items():
                chunk[objid] = img
                if len(chunk) >= self.DEEP_EXTRACT_CHUNK:
                    break
            for objid in chunk.keys():
                del ids_and_images[objid]

            # Call feature extractor
            features = extractor.run(chunk, model_name)

            # Save CNN
            with CodeTimer("Saving %d new CNN " % self.DEEP_EXTRACT_CHUNK, logger):
                nb_rows += DeepFeatures.save(self.session, features)
            self.session.commit()
            
        return "OK, %d CNN features computed and written for %d" % (nb_rows, proj_id)
