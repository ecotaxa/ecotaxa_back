# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# (c) 2021 Jean-Olivier Irisson, GNU General Public License v3
#

#
# @see README.md
# Train a PCA to reduce the number of features produced by a deep feature extractor
# Should be done outside EcoTaxa, just here for generating test data.
#

import pickle
from typing import IO

import pandas as pd  # type: ignore
from sklearn.decomposition import PCA  # type: ignore

from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from ML.Base_ML import MachineLearningBase
from ML.helpers import generator  # type: ignore
from helpers.DynamicLogs import get_logger
from .helpers.tensorflow_cfg import configured_tf as tf  # type: ignore

logger = get_logger(__name__)


class DimensionReducer(MachineLearningBase):
    """
        PCA on dimensions
    """

    def __init__(self, vault: Vault, model_dir: SavedModels):
        """
        :param vault: the vault for finding images
        :param model_dir: directory to read previous model
        """
        super().__init__(vault, model_dir)

    def run(self, csv_in: IO, model_name: str):
        logger.info('Set options')

        batch_size = 16  # size of images batches in GPU memory
        workers = 10  # number of parallel threads to prepare batches
        n_dims = 50  # number of dimensions to keep after dimensionality reduction
        crop = self.read_crop(model_name)

        logger.info('Load feature extractor')

        # save feature extractor
        my_fe = tf.keras.models.load_model(self.model_dir.extractor_path(model_name))

        # get model input shape
        input_shape = my_fe.layers[0].input_shape
        # remove the None element at the start (which is where the batch size goes)
        input_shape = tuple(x for x in input_shape if x is not None)

        logger.info('Load data and extract features for the training set')

        # read DataFrame with image ids, paths and labels
        df = pd.read_csv(csv_in, index_col='id')

        # prepare data batches
        batches = generator.EcoTaxaGenerator(
            images_paths=self.full_img_paths(df.img_path.values),
            input_shape=input_shape,
            labels=None, classes=None,
            batch_size=batch_size, augment=False, shuffle=False, crop=crop)

        # extract features by going through the batches
        features = my_fe.predict(batches, max_queue_size=max(10, workers * 2), workers=workers)

        logger.info('Fit dimensionality reduction')

        # define the PCA
        pca = PCA(n_components=n_dims)
        # fit it to the training data
        pca.fit(features)

        # save it for later application
        with open(self.model_dir.reducer_pickle_path(model_name), 'wb') as pca_file:
            pickle.dump(pca, pca_file)
