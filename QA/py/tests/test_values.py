# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# noinspection PyUnresolvedReferences
from BO.helpers.TSVHelpers import clean_value, clean_value_and_none, to_float


def test_cleans():
    #
    assert clean_value(" rrrr t  YY ") == "rrrr t  YY"
    assert clean_value("NaN") == "NaN"
    assert clean_value("na") == "na"
    assert clean_value("NaN", is_numeric=True) == ""
    assert clean_value("na", is_numeric=True) == ""
    assert clean_value("NaNaNa") == "NaNaNa"

    #
    assert clean_value_and_none(None) == ""
    assert clean_value_and_none("NaN", is_numeric=True) == ""
    assert clean_value_and_none("na", is_numeric=True) == ""
    assert clean_value_and_none("NoNoNo \n") == "NoNoNo"

    #
    assert to_float("") is None
    assert to_float("-inf") is None
    assert to_float("18.5") - 0.5 == 18
    assert to_float("18,5") is None
