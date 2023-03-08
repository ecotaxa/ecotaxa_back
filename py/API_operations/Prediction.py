# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Predict classification on a project. In details, launch a job which will:
# - If requested by the user and possible, compute DeepFeatures on the source projects
# - Use selected features on source projects to train a Random Forest classifier
# - Use the trained classifier on the target project.
#
# Here is just the job registering part, the rest is in GPU_Prediction class.
#
from pathlib import Path
from typing import cast, List

from API_models.filters import ProjectFiltersDict
from API_models.prediction import PredictionReq, PredictionRsp
from BO.Rights import RightsBO, Action
from BO.User import UserIDT
from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from .helpers.JobService import JobServiceBase, ArgsDict
from .helpers.Service import Service

logger = get_logger(__name__)


class PredictForProject(JobServiceBase):
    """ """

    JOB_TYPE = "Prediction"

    def __init__(self, req: PredictionReq, filters: ProjectFiltersDict):
        super().__init__()
        self.req = req
        self.filters = filters
        self.out_path: Path = Path("")
        self.vault = Vault(self.config.vault_dir())
        self.models_dir = SavedModels(self.config)

    def run(self, current_user_id: UserIDT) -> PredictionRsp:
        """
        Initial creation, do security and consistency checks, then create the job.
        """
        _user, _project = RightsBO.user_wants(
            self.session, current_user_id, Action.ANNOTATE, self.req.project_id
        )
        # TODO: more checks, e.g. deep features models consistency
        # OK, go background
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = PredictionRsp(job_id=self.job_id)
        return ret

    def init_args(self, args: ArgsDict) -> ArgsDict:
        args["req"] = self.req.dict()
        args["filters"] = self.filters
        return args

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        json_args["req"] = PredictionReq(**json_args["req"])
        json_args["filters"] = cast(ProjectFiltersDict, json_args["filters"])

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_prediction()

    def do_prediction(self) -> None:
        ...


class PredictionDataService(Service):
    """
    Available models service.
    """

    def get_models(self) -> List[str]:
        return SavedModels(self.config).list()
