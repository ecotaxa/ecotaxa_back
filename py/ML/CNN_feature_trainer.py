# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# (c) 2021 Jean-Olivier Irisson, GNU General Public License v3
#

#
# @see README.md
# CNN features trainer. Should be done outside EcoTaxa, just here for generating test data.
#

# https://github.com/ThelmaPana/plankton_classif_benchmark/blob/8a601ecbaffa3071289329fef647ade2a36fc7a6/models.py#L399
from typing import IO, Optional, Dict

import numpy as np
import pandas as pd  # type: ignore
from sklearn import metrics  # type: ignore

from FS.MachineLearningModels import SavedModels
from FS.Vault import Vault
from ML.Base_ML import MachineLearningBase
from ML.helpers import cnn  # type: ignore # custom functions for CNN generation
from ML.helpers import generator  # type: ignore # custom data generator
from helpers.DynamicLogs import get_logger
from .helpers.tensorflow_cfg import configured_tf as tf  # type: ignore

logger = get_logger(__name__)


class CNNFeatureTrainer(MachineLearningBase):
    """
    Train a deep network for plankton image classification.
    """

    def __init__(self, vault: Vault, model_dir: SavedModels):
        """
        :param vault: the vault for finding images
        :param model_dir: directory to save data/models
        """
        super().__init__(vault, model_dir)

    def run(self, csv_in: IO, model_name: str):

        logger.info('Set options')

        ckpt_dir = self.model_dir.get_checkpoints_dir(model_name)

        # Data generator parameters (see generator.EcoTaxaGenerator)
        batch_size = 16
        augment = True
        # TODO: upscale = True

        # CNN structure (see cnn.Create and cnn.Compile)
        fe_url = 'https://tfhub.dev/google/imagenet/mobilenet_v2_140_224/feature_vector/4'
        input_shape = (224, 224, 3)
        fe_trainable = True
        # fc_layers_sizes = [1792, 896]
        fc_layers_sizes = [600]
        fc_layers_dropout = 0.4
        classif_layer_dropout = 0.2

        # CNN training (see cnn.Train)
        use_class_weight = True
        lr_method = 'decay'
        initial_lr = 0.0005
        decay_rate = 0.97
        loss = 'cce'
        epochs = 2
        workers = 10

        logger.info('Prepare datasets')

        # read DataFrame with image ids, paths and labels
        in_df = pd.read_csv(csv_in, index_col='id')

        # extract a validation set to monitor performance while training
        seed = 1
        # 75% in train
        df_train = in_df.groupby('label').sample(frac=0.75, random_state=seed)
        # the remaining 15% in val
        df_val = in_df.loc[set(in_df.index) - set(df_train.index)]

        # count nb of examples per class in the training set
        class_counts = df_train.groupby('label').size()

        # list classes
        classes = class_counts.index.to_list()

        # generate categories weights
        # i.e. a dict with format { class number : class weight }
        class_weight: Optional[Dict[float, float]]
        if use_class_weight:
            max_count = np.max(class_counts)
            class_weight = {}
            for idx, count in enumerate(class_counts.items()):
                class_weight.update({idx: np.sqrt(max_count / count[1])})
        else:
            class_weight = None

        # define number of classes to train on
        nb_of_classes = len(classes)

        # define data generators
        train_batches = generator.EcoTaxaGenerator(
            images_paths=self.full_img_paths(df_train['img_path'].values),
            input_shape=input_shape,
            labels=df_train['label'].values, classes=classes,
            batch_size=batch_size, augment=augment, shuffle=True)

        val_batches = generator.EcoTaxaGenerator(
            images_paths=self.full_img_paths(df_val['img_path'].values),
            input_shape=input_shape,
            labels=df_val['label'].values, classes=classes,
            batch_size=batch_size, augment=False, shuffle=False)
        # NB: do not shuffle or augment data for validation, it is useless

        total_batches = generator.EcoTaxaGenerator(
            images_paths=self.full_img_paths(in_df['img_path'].values),
            input_shape=input_shape,
            labels=None, classes=None,
            batch_size=batch_size, augment=False, shuffle=False)

        logger.info('Prepare model')

        # try loading the model from a previous training checkpoint
        my_cnn, initial_epoch = cnn.Load(ckpt_dir.as_posix())

        # if nothing is loaded this means the model was never trained
        # in this case, define it
        if my_cnn is not None:
            logger.info('  restart from model trained until epoch ' + str(initial_epoch))
        else:
            logger.info('  define model')
            # define CNN
            my_cnn = cnn.Create(
                # feature extractor
                fe_url=fe_url,
                input_shape=input_shape,
                fe_trainable=fe_trainable,
                # fully connected layer(s)
                fc_layers_sizes=fc_layers_sizes,
                fc_layers_dropout=fc_layers_dropout,
                # classification layer
                classif_layer_size=nb_of_classes,
                classif_layer_dropout=classif_layer_dropout
            )

            logger.info('  compile model')
            # compile CNN
            my_cnn = cnn.Compile(
                my_cnn,
                initial_lr=initial_lr,
                lr_method=lr_method,
                decay_steps=len(train_batches),
                decay_rate=decay_rate,
                loss=loss
            )

        logger.info('Train model')

        # train CNN
        _history = cnn.Train(
            model=my_cnn,
            train_batches=train_batches,
            valid_batches=val_batches,
            epochs=epochs,
            initial_epoch=initial_epoch,
            class_weight=class_weight,
            output_dir=ckpt_dir.as_posix(),
            workers=workers
        )
        # TODO deal with history for restarts
        # TODO check learning rate for restarts

        logger.info('Evaluate model')

        # predict classes for all dataset
        pred = cnn.Predict(
            model=my_cnn,
            batches=total_batches,
            classes=classes,
            workers=workers
        )

        # compute a few scores, just for fun
        in_df['predicted_label'] = pred
        metrics.accuracy_score(y_true=in_df.label, y_pred=in_df.predicted_label)
        metrics.confusion_matrix(y_true=in_df.label, y_pred=in_df.predicted_label)

        logger.info('Create feature extractor')

        # save model
        # TODO: Seems not really needed
        my_cnn.save(self.model_dir.best_model_path(model_name))

        # drop the Dense and Dropout layers to get only the feature extractor
        my_fe = tf.keras.models.Sequential(
            [layer for layer in my_cnn.layers
             if not (isinstance(layer, tf.keras.layers.Dense) |
                     isinstance(layer, tf.keras.layers.Dropout))
             ])
        my_fe.summary(print_fn=logger.info)

        # save feature extractor
        my_fe.save(self.model_dir.extractor_path(model_name))
