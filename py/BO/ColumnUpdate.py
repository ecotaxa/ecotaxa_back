# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A formalized way to update entities
#
from typing import Iterable

from sqlalchemy.sql.functions import current_timestamp
from typing_extensions import TypedDict


class ColUpdate(TypedDict):
    ucol: str
    """ A column name, pseudo-columns AKA free ones, are OK """
    uval: str
    """ The new value to set, always as a string """


class ColUpdateList(list):
    """
        Formalized way of updating entities in the system.
            It's, on purpose, not a Dict as we take provision for futures usage when we need an order.
    """

    def __init__(self, iterable: Iterable[ColUpdate]):
        super().__init__(iterable)

    def as_dict_for_db(self):
        ret = {}
        an_update: ColUpdate
        for an_update in self:
            upd_col = an_update["ucol"]
            ret[upd_col] = an_update["uval"]
            if ret[upd_col] == 'current_timestamp':
                ret[upd_col] = current_timestamp()
        return ret
