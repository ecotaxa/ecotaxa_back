# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Predict classification on a project.
#
from os.path import join
from pathlib import Path
from typing import Dict

from API_models.crud import ProjectFilters
from API_models.prediction import PredictionReq, PredictionRsp
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
from BO.User import UserIDT
from DB import Project
from DB.Project import ProjectIDT
from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from ML.Deep_features_extractor import DeepFeaturesExtractor
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from .helpers.JobService import JobServiceBase
from .helpers.Service import Service

logger = get_logger(__name__)


class PredictForProject(JobServiceBase):
    """

    """
    JOB_TYPE = "Prediction"

    def __init__(self, req: PredictionReq, filters: ProjectFilters):
        super().__init__()
        self.req = req
        self.filters = filters
        self.out_path: Path = Path("")

    def run(self, current_user_id: UserIDT) -> PredictionRsp:
        """
            Initial run, do security and consistency checks, then create the job.
        """
        _user, _project = RightsBO.user_wants(self.session, current_user_id, Action.READ, self.req.project_id)
        # OK, go background
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = PredictionRsp(job_id=self.job_id)
        return ret

    def init_args(self, args: Dict) -> Dict:
        super().init_args(args)
        args["req"] = self.req.dict()
        args["filters"] = self.filters.__dict__
        return args

    @staticmethod
    def deser_args(json_args: Dict):
        json_args["req"] = PredictionRsp(**json_args["req"])
        json_args["filters"] = ProjectFilters(**json_args["filters"])  # type:ignore

    def do_background(self):
        """
            Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_prediction()

    def do_prediction(self) -> None:
        """
            The real job.
        """
        self.out_path = self.temp_for_jobs.base_dir_for(self.job_id)
        req = self.req
        logger.info("Input Param = %s" % (self.req.__dict__,))

        nb_rows = 100
        final_message = "Done."
        self.update_progress(100, final_message)
        done_infos = {"rowcount": nb_rows}
        self.set_job_result(errors=[], infos=done_infos)


class CNNForProject(Service):
    """
        CNN generation for a project
    """

    def __init__(self):
        super().__init__()
        self.vault = Vault(join(self.link_src, 'vault'))
        self.models_dir = SavedModels(self.config)

    def run(self, current_user_id: UserIDT, proj_id: ProjectIDT) -> str:
        """
            Generate the CNN features for a whole project.
            As of 01/10/2021: SCN_zoocam_group1
                              SCN_flowcam_group1
                              SCN_zooscan_group1
                              SCN_uvp5ccelter_group1
        """
        # TODO: rights
        project = self.ro_session.query(Project).get(proj_id)
        assert project is not None
        model_name = project.cnn_network_id
        # TODO: Temp for testing
        model_name = 'zooscan'
        # Get data i.e objects ID and images from the project
        ids_and_images = ProjectBO.get_all_object_ids_with_first_image(self.ro_session, proj_id)
        # Call feature extractor
        extractor = DeepFeaturesExtractor(self.vault, self.models_dir)
        features = extractor.run(ids_and_images, model_name)
        # Save CNN
        return str(features[0])
