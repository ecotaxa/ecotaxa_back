# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

MODELS_LIST_URL = "/ml_models"


def test_ml_models_list(fastapi, caplog):
    """Ensure that only relevant directories are seen as models"""
    caplog.set_level(logging.ERROR)

    rsp = fastapi.get(MODELS_LIST_URL)
    # The test data contains a bit of garbage, only this directory is valid
    assert rsp.json() == [{"name": "zooscan"}]
