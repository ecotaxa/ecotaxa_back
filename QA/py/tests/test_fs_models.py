# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

MODELS_LIST_URL = "/ml_models"


def test_ml_models_list(fastapi):
    """Ensure that only relevant directories are seen as models"""

    rsp = fastapi.get(MODELS_LIST_URL)
    # The test data contains a bit of garbage, only this directory is valid
    assert rsp.json() == [{"name": "zooscan"}]


INSTRUMENT_NETWORKS_URL = "/instruments/cnn_networks"


def test_instrument_cnn_networks(fastapi):
    """Networks are proposed for the instruments their name starts with"""
    rsp = fastapi.get(INSTRUMENT_NETWORKS_URL)
    assert rsp.status_code == 200
    # Only instruments having a network are listed
    assert rsp.json() == {"Zooscan": ["zooscan"]}
    rsp = fastapi.get(INSTRUMENT_NETWORKS_URL, params={"instrument": "Zooscan"})
    assert rsp.json() == {"Zooscan": ["zooscan"]}
    # A known instrument without network
    rsp = fastapi.get(INSTRUMENT_NETWORKS_URL, params={"instrument": "UVP6"})
    assert rsp.json() == {"UVP6": []}
    # An unknown instrument
    rsp = fastapi.get(INSTRUMENT_NETWORKS_URL, params={"instrument": "NotAnInstrument"})
    assert rsp.json() == {}
