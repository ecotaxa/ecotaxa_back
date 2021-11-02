# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# @see README.md
#
# This is step 3 of the whole process but the first step in EcoTaxa
#
# 50 CNN features are extracted from the images and stored into obj_cnn_features DB table.
#

import pickle
from io import StringIO
from typing import IO, Dict

import pandas as pd  # type: ignore

from BO.Object import ObjectIDT
from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger
from .Base_ML import MachineLearningBase
from .helpers import generator  # type: ignore # custom data generator
# Import the library, only after having tweaked it
from .helpers.tensorflow_cfg import configured_tf  # type: ignore

logger = get_logger(__name__)


class DeepFeaturesExtractor(MachineLearningBase):
    """
        Extract CNN features from a set of objects for which renew is necessary.
    """
    BATCH_SIZE = 16  # size of images batches in GPU memory
    WORKERS = 10  # number of parallel threads to prepare batches

    def __init__(self, vault: Vault, model_dir: SavedModels):
        """
        :param vault: the vault for finding images
        :param model_dir: directory to read stored models
        """
        super().__init__(vault, model_dir)

    def run(self, ids_and_images: Dict[ObjectIDT, str], model_name: str):
        logger.info('Load feature extractor and dimensionality reducer')

        input_shape, my_fe, pca = self.load_model(model_name)
        crop = self.read_crop(model_name)

        logger.info('Load data')

        # Prepare a df with input data
        # TODO: Maybe a generator would help for big projects
        df_data = [(obj, fil, None) for obj, fil in ids_and_images.items()]
        df = pd.DataFrame(df_data, columns=["id", "img_path", "label"])
        df.set_index(["id"], inplace=True, verify_integrity=True)

        logger.info('Extract features')

        features_df = self.predict_dataframe(df, input_shape, crop, my_fe, pca)

        return features_df

    def predict_dataframe(self, in_df, input_shape, crop, my_fe, pca):
        """
            Predict what's in in_df and return the result dataframe.
        """
        # prepare data batches
        batches = generator.EcoTaxaGenerator(
            images_paths=self.full_img_paths(in_df.img_path.values),
            input_shape=input_shape,
            labels=None, classes=None,
            # NB: we don't need the labels here, we just run images through the network
            batch_size=self.BATCH_SIZE, augment=False, shuffle=False, crop=crop)
        # extract features by going through the batches
        full_features = my_fe.predict(batches, max_queue_size=max(10, self.WORKERS * 2), workers=self.WORKERS)
        # and reduce their dimension
        reduced_features = pca.transform(full_features)
        # make a result dataframe
        reduced_features_df = pd.DataFrame(reduced_features, index=in_df.index)
        return reduced_features_df

    def load_model(self, model_name):
        """
            Load saved model and PCA params, for the given model.
        """
        my_fe = configured_tf.keras.models.load_model(self.model_dir.extractor_path(model_name))
        # get model input shape
        input_shape = my_fe.layers[0].input_shape
        # remove the None element at the start (which is where the batch size goes)
        input_shape = tuple(x for x in input_shape if x is not None)
        with open(self.model_dir.reducer_pickle_path(model_name), 'rb') as pca_file:
            pca = pickle.load(pca_file)
        return input_shape, my_fe, pca

    def test(self, csv_in: IO, model_name: str) -> StringIO:
        """
            Try the model.
        """
        logger.info('TEST: Load feature extractor and dimensionality reducer')

        input_shape, my_fe, pca = self.load_model(model_name)

        logger.info('TEST: Load data and extract features')

        # read DataFrame with image ids, paths and labels
        # NB: those would be in the database in EcoTaxa
        df = pd.read_csv(csv_in, index_col='id')

        reduced_features_df = self.predict_dataframe(df, input_shape, my_fe, pca)

        logger.info('TEST: Dumping a few rows')

        ret = StringIO()
        reduced_features_df.to_csv(ret)

        return ret
