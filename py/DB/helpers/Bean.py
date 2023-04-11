# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional

from .ORM import _analyze_cols, Model


class Bean(dict):
    """
    Holder with just fields & value
    """

    # TODO: A proper subclass with known fields

    # def __init__(self, cols, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.cols = cols

    def __getattr__(self, attr):
        """To support e.g. obj.latitude"""
        try:
            return self[attr]
        except KeyError:
            raise AttributeError()

    def __setattr__(self, key, value):
        """To support e.g. obj.prjid = 1"""
        # assert key in self.cols
        self[key] = value

    def nb_fields_from(self, fields_set: set):
        return len(fields_set.intersection(self.keys()))


def bean_of(an_obj: Optional[Model]) -> Optional[Bean]:
    """
    Return a plain bean from an ORM-mapped object. All keys are nullified for safety.
    None in, None out.
    :param an_obj:
    :return:
    """
    if an_obj is None:
        return None
    ret = Bean()
    to_copy, to_clear = _analyze_cols(an_obj.__table__)
    for a_col in to_clear:
        ret[a_col] = None
    for a_col in to_copy:
        ret[a_col] = getattr(an_obj, a_col)
    return ret
