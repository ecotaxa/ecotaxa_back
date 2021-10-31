# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# (c) 2021 Jean-Olivier Irisson, GNU General Public License v3
#

#
# @see README.md
#
from typing import List, Tuple

import numpy as np  # type: ignore
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

    def __init__(self):
        # We can build the classifier right away, it's just allocation
        self.cls = RandomForestClassifier(n_estimators=self.N_ESTIMATORS,
                                          min_samples_leaf=self.MIN_SAMPLES_LEAF, n_jobs=self.WORKERS,
                                          class_weight=self.CLASS_WEIGHT,
                                          verbose=True)  # TODO: verbose sends logs we can't see :(

    def learn_from(self, training_samples: np.ndarray, target_values: np.ndarray):
        """
            Learn the classifier from given data.
        """
        self.cls.fit(training_samples, target_values)

    def predict(self, to_predict: np.ndarray) -> Tuple[ClassifIDListT, List[float]]:
        """
            Predict, i.e. return the most likely target value (classif_id) for the given objects.
            Input np array must have the same columns as in training samples during build.
            For each input line, the returned array contain the best guessed classification ID, and its score.
        """
        predict_result = self.cls.predict_proba(to_predict)
        max_proba = np.argmax(predict_result, axis=1)
        classif_ids = [int(self.cls.classes_[mc]) for mc in max_proba]
        scores = [r[mc] for mc, r in zip(max_proba, predict_result)]
        return classif_ids, scores

