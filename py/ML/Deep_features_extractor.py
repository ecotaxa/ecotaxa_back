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

import dataset  # custom data generator
import pandas as pd

from helpers.DynamicLogs import get_logger
# Import the library, only after having tweaked it
from .helpers.tensorflow_cfg import configured_tf

logger = get_logger(__name__)


class DeepFeaturesExtractor(object):
    """
        Input: a set of images, from a set of objects.
        Ouput: stored CNN features for the images.
        Configuration: from files
    """
    BATCH_SIZE = 16  # size of images batches in GPU memory
    WORKERS = 10  # number of parallel threads to prepare batches

    def __init__(self):
        pass

    def run(self):
        logger.info('Set options')

        logger.info('Load feature extractor and dimensionality reducer')

        my_fe = configured_tf.keras.models.load_model('out/feature_extractor')
        # get model input shape
        input_shape = my_fe.layers[0].input_shape
        # remove the None element at the start (which is where the batch size goes)
        input_shape = tuple(x for x in input_shape if x is not None)

        with open('out/dim_reducer.pickle', 'rb') as pca_file:
            pca = pickle.load(pca_file)

        logger.info('Load data and extract features')

        for source in ['training', 'unknown']:
            # read DataFrame with image ids, paths and labels
            # NB: those would be in the database in EcoTaxa
            df = pd.read_csv('data/' + source + '_labels.csv', index_col='id')

            # prepare data batches
            batches = dataset.EcoTaxaGenerator(
                images_paths=df.img_path.values,
                input_shape=input_shape,
                labels=None, classes=None,
                # NB: we don't need the labels here, we just run images through the network
                batch_size=self.BATCH_SIZE, augment=False, shuffle=False)

            # extract features by going through the batches
            full_features = my_fe.predict(batches, max_queue_size=max(10, self.WORKERS * 2), workers=self.WORKERS)
            # and reduce their dimension
            reduced_features = pca.transform(full_features)

            # save them to disk
            reduced_features_df = pd.DataFrame(reduced_features, index=df.index)
            reduced_features_df.to_csv('data/' + source + '_deep_features.csv')
