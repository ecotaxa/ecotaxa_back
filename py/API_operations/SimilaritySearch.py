# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2022-2024 LOVNOWER : Amblard, Colin, Irisson, Reutenauer (UPMC-CNRS-FOTONOWER)
#
# Similarity Search on a project.
#
from typing import cast, List

from API_models.filters import ProjectFiltersDict
from API_models.simsearch import SimilaritySearchReq, SimilaritySearchRsp
from API_operations.FeatureExtraction import FeatureExtractionForProject
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from DB.helpers.Direct import text
from BO.Rights import RightsBO, Action
from BO.User import UserIDT
from BO.ObjectSet import DescribedObjectSet
from BO.Prediction import DeepFeatures
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from .helpers.Service import Service

logger = get_logger(__name__)


class SimilaritySearchForProject(Service):
    """ """
    NUM_NEIGHBORS = 100

    def __init__(self, req: SimilaritySearchReq, filters: ProjectFiltersDict) -> None:
        super().__init__()
        self.req = req
        self.filters = filters

    
    def similarity_search(self, current_user) -> SimilaritySearchRsp:
        """
        Similarity search on a project.
        """
        _user, project = RightsBO.user_wants(
            self.session, current_user, Action.ANNOTATE, self.req.project_id
        )

        # Check that deep features are present for given project.
        ids_and_images = DeepFeatures.find_missing(self.ro_session, self.req.project_id)
        if len(ids_and_images) != 0:

            # Launch a feature extraction job
            feature_extractor_selected = project.cnn_network_id != ""
            if feature_extractor_selected:
                with FeatureExtractionForProject(self.req.project_id) as sce:
                    sce.run(current_user)
                
                rsp : SimilaritySearchRsp = SimilaritySearchRsp(
                    neighbor_ids=[],
                    sim_scores=[],
                    message="Missing CNN features, feature extraction job launched",
                )
                return rsp

            # No feature extractor selected, so we cannot extract features
            else:
                rsp = SimilaritySearchRsp(
                    neighbor_ids=[],
                    sim_scores=[],
                    message="Missing CNN features, please select a feature extractor",
                )
                return rsp

        target_id = self.req.target_id
        limit = self.NUM_NEIGHBORS

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.ro_session, project, current_user, self.filters
        )
        from_, where_clause, params = object_set.get_sql()
        where_clause_sql = where_clause.get_sql()
        if where_clause_sql != " ":
            where_clause_sql += " AND objcnnid = obh.objid"
        else:
            where_clause_sql = "WHERE objcnnid = obh.objid"

        query = f"""
            SELECT objcnnid, features::vector <-> (
                SELECT features FROM {ObjectCNNFeatureVector.__tablename__}
                WHERE objcnnid={target_id}
            )::vector AS dist
            FROM {ObjectCNNFeatureVector.__tablename__}, {from_.get_sql()}
            {where_clause_sql}
            ORDER BY dist LIMIT {limit};
        """

        result = self.ro_session.execute(text(query), params).fetchall()
        neighbors = [res["objcnnid"] for res in result]
        distances = [res["dist"] for res in result]
        scores = [round(1 - (dist / distances[-1]), 4) for dist in distances]

        rsp = SimilaritySearchRsp(
            neighbor_ids=neighbors,
            sim_scores=scores,
            message="Success"
        )

        return rsp
