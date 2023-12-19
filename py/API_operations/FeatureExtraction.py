# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Extract deep DeepFeatures on a project.
#
from typing import Dict, List, Tuple

import numpy as np

from BO.Rights import RightsBO, Action
from BO.User import UserIDT
from DB.Project import ProjectIDT, Project
from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger, LogsSwitcher
from .helpers.JobService import JobServiceOnProjectBase, ArgsDict

logger = get_logger(__name__)


class FeatureExtractionForProject(JobServiceOnProjectBase):
    """ """

    JOB_TYPE = "FeatureExtraction"

    def __init__(self, prj_id: ProjectIDT) -> None:
        super().__init__(prj_id)
        self.vault = Vault(self.config.vault_dir())
        self.models_dir = SavedModels(self.config)
    
    def run(self, current_user_id: UserIDT) -> None:
        """
        Initial creation, do security and consistency checks, then create the job.
        """
        _user, _project = RightsBO.user_wants(
            self.session, current_user_id, Action.ANNOTATE, self.prj_id
        )
        # TODO: more checks, e.g. deep features models consistency
        # Security OK, create pending job
        self.create_job(self.JOB_TYPE, current_user_id)

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            self.ensure_deep_features_job()
    
    def ensure_deep_features_job(self) -> None:
        ...
    