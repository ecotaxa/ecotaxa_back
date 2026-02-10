# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# (c) 2021 Jean-Olivier Irisson, GNU General Public License v3
#

#
# @see README.md
#
from typing import List, Tuple

import numpy as np  # type: ignore

try:
    from sklearnex import patch_sklearn, unpatch_sklearn  # type: ignore
    from sklearnex.ensemble import RandomForestClassifier as RandomForestClassifierEx
except ImportError as e:
    pass
from sklearn.ensemble import RandomForestClassifier  # type: ignore

from BO.Classification import ClassifIDListT


class OurRandomForestClassifier(object):
    """
    A random forest classifier, tuned for EcoTaxa
    """

    # Tuning
    N_ESTIMATORS = 300
    MIN_SAMPLES_LEAF = 5
    CLASS_WEIGHT = "balanced"
    # CPU resources
    WORKERS = 6

    FULL_INTELEX = False

    def __init__(self) -> None:
        # We can build the classifier right away, it's just allocation
        if self.FULL_INTELEX:
            self.rfc = RandomForestClassifierEx(
                n_estimators=self.N_ESTIMATORS,
                min_samples_leaf=self.MIN_SAMPLES_LEAF,
                n_jobs=self.WORKERS,
                class_weight=self.CLASS_WEIGHT,
                verbose=True,
                random_state=420,
            )
        else:
            self.rfc = RandomForestClassifier(
                n_estimators=self.N_ESTIMATORS,
                min_samples_leaf=self.MIN_SAMPLES_LEAF,
                n_jobs=self.WORKERS,
                class_weight=self.CLASS_WEIGHT,
                verbose=True,
                random_state=420,
            )  # TODO: verbose sends logs we can't see :(

    def learn_from(self, training_samples: np.ndarray, target_values: np.ndarray):
        """
        Learn the classifier from given data.
        """
        self.rfc.fit(training_samples, target_values)

        if not self.FULL_INTELEX:
            patch_sklearn()
            from sklearn.ensemble import RandomForestClassifier as PatchedRF

            cls_ex = PatchedRF()
            # Manually copy the fitted attributes
            # This works if the class names match via the patch
            for attr in self.rfc.__dict__:
                if attr.endswith("_") or attr.startswith("n_"):
                    setattr(cls_ex, attr, getattr(self.rfc, attr))
            unpatch_sklearn()
            self.rfc = cls_ex

    def predict(self, to_predict: np.ndarray) -> Tuple[ClassifIDListT, List[float]]:
        """
        Predict, i.e. return the most likely target value (classif_id) for the given objects.
        Input np array must have the same columns as in training samples during build.
        For each input line, the returned array contains the best guessed classification ID, and its score.
        """
        predict_result = self.rfc.predict_proba(to_predict)
        max_proba = np.argmax(predict_result, axis=1)
        classif_ids = [int(self.rfc.classes_[mc]) for mc in max_proba]
        scores = [r[mc] for mc, r in zip(max_proba, predict_result)]
        return classif_ids, scores

    def predict_all(
        self, to_predict: np.ndarray
    ) -> Tuple[List[ClassifIDListT], List[List[float]]]:
        """
        Predict, i.e. return all target values (classif_id) for the given objects in descending score order.
        Input np array must have the same columns as in training samples during build.
        For each input line, the returned array contains all guessed classification ID, and their scores.
        """
        predict_result = self.rfc.predict_proba(to_predict)
        classif_ids = list()
        scores = list()
        for obj_probas in predict_result:
            # Get the order of predicted probabilities in descending order
            sorted_indexes = np.flip(np.argsort(obj_probas))
            # Add all predictions to result
            classif_ids.append(self.rfc.classes_[sorted_indexes].tolist())
            scores.append(obj_probas[sorted_indexes].tolist())
        return classif_ids, scores
