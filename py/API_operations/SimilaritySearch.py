# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2022-2024 LOVNOWER : Amblard, Colin, Irisson, Reutenauer (UPMC-CNRS-FOTONOWER)
#
# Similarity Search on a project.
#

from API_models.filters import ProjectFiltersDict
from API_models.simsearch import SimilaritySearchReq, SimilaritySearchRsp
from BO.ObjectSet import DescribedObjectSet
from BO.Prediction import DeepFeatures
from BO.Rights import RightsBO, Action
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from DB.helpers.Direct import text
from helpers.DynamicLogs import get_logger

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
            feature_extractor_selected = (
                project.cnn_network_id is not None and project.cnn_network_id != ""
            )
            if feature_extractor_selected:
                # with FeatureExtractionForProject(self.req.project_id) as sce:
                #     #                    sce.run(current_user)
                #     sce.run_in_background()

                rsp: SimilaritySearchRsp = SimilaritySearchRsp(
                    neighbor_ids=[],
                    sim_scores=[],
                    message="Project has a feature extractor, but no feature. Predict once to generate features.",
                )
                return rsp

            # No feature extractor selected, so we cannot extract features
            else:
                rsp = SimilaritySearchRsp(
                    neighbor_ids=[],
                    sim_scores=[],
                    message="Project has no feature extractor, choose one in project settings.",
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

        # VR hack 071124 : j'ai crée cette fonction
        # CREATE OR REPLACE FUNCTION euclidean_distance(a real[], b real[]) RETURNS float AS $$ DECLARE sum float := 0; i int := 1; BEGIN IF array_upper(a, 1) <> array_upper(b, 1) THEN RAISE EXCEPTION 'Les vecteurs doivent avoir la même taille'; END IF; FOR i IN 1..array_upper(a, 1) LOOP sum := sum + (a[i] - b[i]) ^ 2; END LOOP; RETURN sqrt(sum); END; $$ LANGUAGE plpgsql IMMUTABLE;
        #             SELECT objcnnid, euclidean_distance(features, ( SELECT features FROM {ObjectCNNFeatureVector.__tablename__}
        #              WHERE objcnnid = {target_id} )) AS dist

        # ou plutot
        # CREATE EXTENSION cube; CREATE INDEX features_idx ON obj_cnn_features_vector USING GIST (cube(features));

        # query = f"""
        # SELECT objcnnid, cube(features) <-> cube((SELECT features FROM {ObjectCNNFeatureVector.__tablename__}
        # WHERE objcnnid={target_id})) AS dist
        #     FROM {ObjectCNNFeatureVector.__tablename__}, {from_.get_sql()}
        #     {where_clause_sql}
        #     ORDER BY dist LIMIT {limit};
        # """

        query = f"""
        SET LOCAL ivvflat.probes = 10;
        SELECT objcnnid, features<->(SELECT features FROM {ObjectCNNFeatureVector.__tablename__}
        WHERE objcnnid={target_id}) AS dist
        FROM {ObjectCNNFeatureVector.__tablename__}, {from_.get_sql()}
            {where_clause_sql}
        ORDER BY dist LIMIT {limit}
        """

        result = self.ro_session.execute(text(query), params).fetchall()
        neighbors = [res["objcnnid"] for res in result]
        distances = [res["dist"] for res in result]
        scores = [round(1 - (dist / distances[-1]), 4) for dist in distances]

        rsp = SimilaritySearchRsp(
            neighbor_ids=neighbors, sim_scores=scores, message="Success"
        )

        return rsp
