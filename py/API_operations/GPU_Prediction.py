# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Predict classification on a project. In details, launch a job which will:
# - If requested by the user and possible, compute DeepFeatures on the source projects
# - Use selected features on source projects to train a Random Forest classifier
# - Use the trained classifier on the target project.
#
from typing import Dict, List, Tuple

import numpy as np

from API_models.prediction import PredictionReq
from BO.Classification import ClassifIDListT
from BO.ObjectSet import DescribedObjectSet, EnumeratedObjectSet, ObjectIDListT
from BO.Prediction import DeepFeatures
from BO.Project import ProjectBO
from BO.ProjectSet import LimitedInCategoriesProjectSet, FeatureConsistentProjectSet
from BO.Rights import RightsBO, Action
from DB.Project import ProjectIDT, Project
from DB.helpers import Result
from DB.helpers.Direct import text
from ML.Deep_features_extractor import DeepFeaturesExtractor
from ML.Random_forest_classifier import OurRandomForestClassifier
from helpers.DynamicLogs import get_logger
# TODO: Move somewhere else
from helpers.Timer import CodeTimer
from .ObjectManager import ObjectManager
from .Prediction import PredictForProject

logger = get_logger(__name__)

# Remove job type for base class, so during run the flow ends here
PredictForProject.JOB_TYPE = ""


class GPUPredictForProject(PredictForProject):
    """
    Part of the prediction which needs special HW and libs.
    """

    JOB_TYPE = "Prediction"

    # Remove columns with absent values % exceeding the constant below
    MAX_NO_VAL = 0.25

    # Prohibit a learning set larger than below, it takes too many resources
    MAX_LEARNING_SET_SIZE = 350000

    def do_prediction(self) -> None:
        """
        The real job.
        """
        self.out_path = self.temp_for_jobs.base_dir_for(self.job_id)
        req = self.req
        logger.info("Input Param = %s", self.req.__dict__)

        _user, tgt_prj = RightsBO.user_wants(
            self.session, self._get_owner_id(), Action.ANNOTATE, self.req.project_id
        )

        if req.use_scn:
            self.update_progress(5, "Ensuring deep learning features are present")
            self.ensure_deep_features(tgt_prj)

        self.update_progress(10, "Retrieving learning set data")
        (
            np_feature_vals,
            classif_ids,
            used_features,
            np_medians_per_feat,
        ) = self.build_learning_set(req)
        ls_size = np_feature_vals.shape[0]
        if ls_size > self.MAX_LEARNING_SET_SIZE:
            self.report_ls_too_large(ls_size)
            return

        self.update_progress(20, "Training the classifier")
        classifier = self.build_classifier(np_feature_vals, classif_ids)

        self.update_progress(25, "Retrieving objects to classify")
        target_result = self.select_target(tgt_prj, used_features)
        nb_rows = self.classify(
            target_result, classifier, used_features, np_medians_per_feat
        )

        final_message = "New category set on %d objects." % nb_rows
        self.update_progress(100, final_message)
        done_infos = {"rowcount": nb_rows}
        self.set_job_result(errors=[], infos=done_infos)

    def report_ls_too_large(self, ls_size: int) -> None:
        logger.error(
            "Learning set too large: {} vs machine maximum of {}".format(
                ls_size, self.MAX_LEARNING_SET_SIZE
            )
        )
        logger.info(
            """
To correct the situation, you might:
In first step 'Choice of Learning Set data source', use fewer example projects.  
In second step 'Choice of Learning Set categories and size', where the learning set size is displayed:
    - lower the number of objects per category (currently set at {}). 
    - unselect some categories by clicking in '# source' column.""".format(
                self.req.learning_limit
            )
        )
        self.set_job_result(
            errors=["Learning set is too large"], infos={"status": "error"}
        )
        self.update_progress(100, "Done")

    def build_learning_set(
        self, req: PredictionReq
    ) -> Tuple[np.ndarray, ClassifIDListT, List[str], Dict[str, float]]:
        """
        Build the learning set from DB data & req instructions.
        :returns - A matrix in which each line contains the features for selected (validated) objects.
                 - The classification for each object, in a list, same order as the matrix lines of course.
                 - The object features AKA DB columns used for extraction, e.g. 'fre.feret' or 'fre.circ'.
                   The same list has to be used for objects to predict.
                 - Medians of existing values per feature, which was used for replacement of missing values
                   inside the matrix, and hence needs to be used in objects to predict as well.
        """
        learning_set = LimitedInCategoriesProjectSet(
            self.ro_session,
            req.source_project_ids,
            req.features,
            req.learning_limit,
            req.categories,
        )
        features = list(req.features)
        nb_features = len(features)
        # Read DB values all into memory.
        np_learning_set, obj_ids, classif_ids = learning_set.np_read_all()
        obj_count = len(obj_ids)
        logger.info("Learning set is %s lines * %s columns", obj_count, nb_features)

        # Compute medians & variance per _present_ feature
        np_medians_per_feat, np_variances_per_feat = learning_set.np_stats(
            np_learning_set
        )
        logger.debug("Numpy medians: %s", np_medians_per_feat)
        logger.debug("Numpy variances: %s", np_variances_per_feat)

        # Absent i.e. NaN values
        np_nans = np.count_nonzero(np.isnan(np_learning_set), axis=0)
        np_nans_per_feat = {feat: nanc for feat, nanc in zip(features, np_nans)}
        logger.debug("Numpy NaNs: %s", np_nans_per_feat)

        to_del = {}
        # Remove columns with too many NaN
        for a_feat, nan_count in np_nans_per_feat.items():
            missing_ratio = nan_count / obj_count
            if missing_ratio > self.MAX_NO_VAL:
                to_del[a_feat] = "%.02f%% missing" % (missing_ratio * 100)
        # Remove columns with 0 variance, i.e. constant
        for a_feat, vari in np_variances_per_feat.items():
            if a_feat in to_del:
                continue
            if vari == 0:
                to_del[a_feat] = (
                    "Constant :%s" % np_learning_set[0, features.index(a_feat)]
                )
        # Replace NaNs with median
        replacements = {}
        for a_feat, nan_count in np_nans_per_feat.items():
            if (a_feat in to_del) or nan_count == 0:
                continue
            ndx = features.index(a_feat)
            med = np_medians_per_feat[a_feat]
            nb_repls = 0
            for line in range(obj_count):
                if np.isnan(np_learning_set[line, ndx]):
                    np_learning_set[line, ndx] = med
                    nb_repls += 1
            replacements[a_feat] = (nb_repls, med)
        logger.info("NaN replacements: %s", replacements)

        # Drop useless features
        to_del_ndx = [features.index(a_feat) for a_feat in to_del.keys()]
        clean_np_features = np.delete(np_learning_set, to_del_ndx, axis=1)
        logger.info("Dropped features: %s", to_del)
        used_features = [a_feat for a_feat in features if a_feat not in to_del]

        # In case, add deep features
        if self.req.use_scn:
            self.update_progress(15, "Retrieving deep features")
            logger.info("Adding 50 deep features")
            np_deep_features = DeepFeatures.np_read_for_objects(
                self.ro_session, obj_ids
            )
            clean_np_features = np.concatenate(
                [clean_np_features, np_deep_features], axis=1
            )

        # Apply pre-mapping
        classif_ids = [
            req.pre_mapping.get(classif_id, classif_id) for classif_id in classif_ids
        ]

        return clean_np_features, classif_ids, used_features, np_medians_per_feat

    @staticmethod
    def build_classifier(
        features: np.ndarray, classif_ids: ClassifIDListT
    ) -> OurRandomForestClassifier:
        """
        Build the classifier model and train it with the data & target ids.
        """
        logger.info("Training the classifier")
        ret = OurRandomForestClassifier()
        ret.learn_from(features, classif_ids)
        logger.info("Done training the classifier")

        return ret

    def select_target(self, tgt_project: Project, features: List[str]) -> Result:
        """
        Return an opened cursor for looping over objects to classify.
        """
        # Prepare a where clause and parameters from filter
        user_id = self._get_owner_id()
        filters = self.filters
        filters["statusfilter"] = "UP"  # TODO: It overrides other filters
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.ro_session, tgt_project, user_id, filters
        )
        free_columns_mappings = object_set.mapping.object_mappings
        sel_cols = ObjectManager.add_return_fields(features, free_columns_mappings)
        from_, where_clause, params = object_set.get_sql(
            order_clause=None, select_list=sel_cols
        )
        sql = (
            "SELECT obh.objid, NULL "
            + sel_cols
            + " FROM "
            + from_.get_sql()
            + where_clause.get_sql()
        )
        logger.info("Execute SQL : %s" % sql)
        res: Result = self.ro_session.execute(text(sql), params)
        return res

    CHUNK_SIZE = 10000

    def classify(
        self,
        tgt_res: Result,
        classifier: OurRandomForestClassifier,
        features: List[str],
        np_medians_per_feat: Dict[str, float],
    ) -> int:
        """
        Do the classification job itself, read lines from the DB, classify them and write-back the result.
        """
        total_rows = tgt_res.rowcount  # type:ignore # case1
        done_count = 0
        nb_changes = 0
        while True:
            obj_ids: ObjectIDListT = []
            unused: ClassifIDListT = []
            np_chunk = FeatureConsistentProjectSet.np_read(
                tgt_res, self.CHUNK_SIZE, features, obj_ids, unused, np_medians_per_feat
            )
            if self.req.use_scn:
                np_deep_features_chunk = DeepFeatures.np_read_for_objects(
                    self.ro_session, obj_ids
                )
                np_chunk = np.concatenate([np_chunk, np_deep_features_chunk], axis=1)
            logger.info("One chunk of %d", len(obj_ids))
            classif_ids, scores = classifier.predict(np_chunk)
            target_obj_set = EnumeratedObjectSet(self.session, obj_ids)
            # TODO: Remove the keep_logs flag, once sure the new algo is better
            nb_upd, all_changes = target_obj_set.classify_auto(
                classif_ids, scores, keep_logs=True
            )
            nb_changes += nb_upd
            logger.info("Changes :%s", str(all_changes)[:1000])
            self.session.commit()
            if len(obj_ids) < self.CHUNK_SIZE:
                break
            done_count += len(obj_ids)
            progress = 25 + (75 * done_count / total_rows)
            self.update_progress(progress, "Classified %d rows" % done_count)
        # Propagate changes to update projects_taxo_stat
        ProjectBO.update_taxo_stats(self.session, self.req.project_id)
        self.session.commit()
        logger.info("Classify done.")
        return nb_changes

    def ensure_deep_features(self, tgt_project: Project) -> None:
        """
        Ensure that deep features are present for all involved projects.
        As of 01/10/2021: SCN_zoocam_group1
                          SCN_flowcam_group1
                          SCN_zooscan_group1
                          SCN_uvp5ccelter_group1
        """
        model_name = tgt_project.cnn_network_id
        assert model_name, "Target project has no cnn_network_id"
        for a_projid in [tgt_project.projid] + self.req.source_project_ids:
            diag = self._ensure_deep_features_for(a_projid, model_name)
            logger.info(diag)

    DEEP_EXTRACT_CHUNK = 10000

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
