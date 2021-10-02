# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A prediction is the output of an automatic classification process.
# This is heavily based on machine learning algorithms.
#

from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class Predictor(object):
    """
        Do what's needed in order to generate an OK prediction, AKA automatic classification, of the vignette.
    """
    def __init__(self):
        pass

