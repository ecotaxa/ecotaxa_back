# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A bit of SQL encapsulation.
#
import re
from decimal import Decimal
from typing import Union, List, Dict, Optional, Set

# A dict for sending parametrized SQL to the engine
SQLParamDict = Dict[str, Union[int, float, Decimal, str, List[int], List[str]]]


class FromClause(object):
    """
        A 'from' clause in SQL. List of joined table expressions.
    """

    def __init__(self, first: str):
        self.joins = [first]

    def __add__(self, other) -> 'FromClause':
        self.joins.append(other)
        return self

    def get_sql(self):
        return "\n  JOIN ".join(self.joins)

    def replace_table(self, before: str, after: str):
        repl = []
        before += " "
        after += " "
        for a_join in self.joins:
            if before in a_join:
                a_join = a_join.replace(before, after)
            repl.append(a_join)
        self.joins.clear()
        self.joins.extend(repl)

    def remove_if_refers_to(self, table_name: str):
        self.joins = [a_join for a_join in self.joins
                      if table_name not in a_join]


class WhereClause(object):
    """
        A 'where' clause in SQL. List of 'and' clauses.
    """

    def __init__(self):
        self.ands = []

    def __mul__(self, other) -> 'WhereClause':
        self.ands.append(other)
        return self

    def get_sql(self):
        if len(self.ands) > 0:
            return "\nWHERE " + "\n  AND ".join(self.ands)
        else:
            return " "

    def replace_reference(self, chunk_from, chunk_to):
        self.ands = [an_and.replace(chunk_from, chunk_to)
                     for an_and in self.ands]

    def remove_if(self, chunk):
        self.ands = [an_and for an_and in self.ands
                     if an_and != chunk]

    # Not completely exact but enough
    COL_RE = re.compile(r"\b(\w+)\.(\w+)\b", re.ASCII)

    def referenced_columns(self, with_prefices=True) -> Set[str]:
        ret = []
        for an_and in self.ands:
            for a_match in self.COL_RE.finditer(an_and):
                if with_prefices:
                    ret.append(a_match.group(0))
                else:
                    ret.append(a_match.group(2))
        return set(ret)


class OrderClause(object):
    """
        An 'order by' clause in SQL. List of columns/aliases.
    """

    def __init__(self):
        self.expressions: List[str] = []
        self.columns: List[str] = []

    def add_expression(self, alias: str, expr: str, asc_or_desc: Optional[str]) -> None:
        if asc_or_desc is None:
            asc_or_desc = "ASC"
        self.expressions.append("%s.%s %s" % (alias, expr, asc_or_desc))
        self.columns.append(alias + "." + expr)

    def referenced_columns(self, with_prefices=True) -> Set[str]:
        if with_prefices:
            return set(self.columns)
        else:
            return set([a_col.split(".")[1] for a_col in self.columns])

    def get_sql(self) -> str:
        return "\nORDER BY " + ", ".join(self.expressions)

    def replace(self, chunk_from, chunk_to):
        self.expressions = [a_exp.replace(chunk_from, chunk_to)
                            for a_exp in self.expressions]
        self.columns = [a_col.replace(chunk_from, chunk_to)
                        for a_col in self.columns]

    def clone(self) -> 'OrderClause':
        ret = OrderClause()
        ret.expressions = self.expressions[:]
        ret.columns = self.columns[:]
        return ret
