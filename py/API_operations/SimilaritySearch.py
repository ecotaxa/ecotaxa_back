# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Similarity Search on a project.
#
from typing import cast, List

from API_models.filters import ProjectFiltersDict
from API_models.simsearch import SimilaritySearchReq, SimilaritySearchRsp
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from DB.helpers.Direct import text
from BO.Rights import RightsBO, Action
from BO.User import UserIDT
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from .helpers.JobService import JobServiceBase, ArgsDict
from .helpers.Service import Service

logger = get_logger(__name__)


class SimilaritySearchForProject(JobServiceBase):
    """ """
    JOB_TYPE = "SimilaritySearch"
    NUM_NEIGHBORS = 100

    def __init__(self, req: SimilaritySearchReq, filters: ProjectFiltersDict) -> None:
        super().__init__()
        self.req = req
        self.filters = filters
    
    def run(self, current_user_id: int) -> SimilaritySearchRsp:
        """
        Initial creation, do security and consistency checks, then create the job.
        """
        _user, _project = RightsBO.user_wants(
            self.session, current_user_id, Action.ANNOTATE, self.req.project_id
        )

        # Security OK, create pending job
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = SimilaritySearchRsp(job_id=self.job_id)
        return ret

    def init_args(self, args: ArgsDict) -> ArgsDict:
        args["req"] = self.req.dict()
        args["filters"] = self.filters
        return args

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        json_args["req"] = SimilaritySearchReq(**json_args["req"])
        json_args["filters"] = cast(ProjectFiltersDict, json_args["filters"])

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_similarity_search()
    
    def do_similarity_search(self) -> None:
        """
        Similarity search on a project.
        """
        session = self.ro_session
        target_id = self.req.target_id
        limit = self.NUM_NEIGHBORS

        query = f"""
            SELECT objcnnid, features <-> (
                SELECT features FROM {ObjectCNNFeatureVector.__tablename__}
                WHERE objcnnid={target_id}
            ) AS dist
            FROM {ObjectCNNFeatureVector.__tablename__}
            ORDER BY dist LIMIT {limit};
        """

        result = session.execute(text(query))
        neighbors = [res["objcnnid"] for res in result]
        self.set_job_result(errors=[], infos={"neighbor_ids": neighbors})