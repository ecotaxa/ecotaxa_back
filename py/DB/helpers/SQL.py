# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A bit of SQL encapsulation.
#
from typing import Union, List, Dict

# A dict for sending parametrized SQL to the engine
SQLParamDict = Dict[str, Union[int, float, str, List[int], List[str]]]


class WhereClause(object):
    """
        A 'where' clause in SQL. List of 'and' clauses.
    """

    def __init__(self):
        self.ands = []

    def __mul__(self, other):
        self.ands.append(other)
        return self

    def get_sql(self):
        return "where " + "and \n".join(self.ands)
