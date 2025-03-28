# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A bit of SQL encapsulation.
#
import re
from decimal import Decimal
from typing import Union, List, Dict, Optional, Set, Generator, Tuple

# A dict for sending parametrized SQL to the engine
SQLParamDict = Dict[str, Union[int, float, Decimal, str, List[int], List[str]]]


class SelectClause(object):
    """
    List of selected expressions, eventually aliased.
    """

    __slots__ = ("expressions", "aliases")

    def __init__(self):
        self.expressions = []
        self.aliases = []

    def add(self, expr: str, alias: Optional[str] = None) -> "SelectClause":
        self.expressions.append(expr)
        self.aliases.append(alias)
        return self

    def get_sql(self) -> str:
        aliased = [
            expr + (f" AS {alias}" if alias else "")
            for expr, alias in zip(self.expressions, self.aliases)
        ]
        ret = "SELECT " + ", ".join(aliased)
        return ret


class FromClause(object):
    """
    A 'from' clause in SQL. List of joined table expressions.
    """

    __slots__ = ("joins", "left_joins", "lateral_joins")

    def __init__(self, first: str):
        self.joins = [first]
        self.left_joins: Set[str] = set()
        self.lateral_joins: Set[str] = set()

    def __add__(self, other) -> "FromClause":
        self.joins.append(other)
        return self

    def get_sql(self) -> str:
        sqls = [self.joins[0]]
        for a_join in self.joins[1:]:
            lateral = "LATERAL " if a_join in self.lateral_joins else ""
            if a_join in self.left_joins:
                sqls.append("LEFT JOIN " + lateral + a_join)
            else:
                sqls.append("JOIN " + lateral + a_join)
        return "\n ".join(sqls)

    def replace_table(self, before: str, after: str) -> None:
        repl = []
        before += " "
        after += " "
        for a_join in self.joins:
            if before in a_join:
                a_join = a_join.replace(before, after)
            repl.append(a_join)
        self.joins.clear()
        self.joins.extend(repl)

    def remove_if_refers_to(self, table_name: str) -> None:
        self.joins = [a_join for a_join in self.joins if table_name not in a_join]

    def set_outer(self, join_start: str) -> None:
        """Signal that the clause starting with join_start should be a LEFT one"""
        self._add_if_starts(self.left_joins, join_start)

    def set_lateral(self, join_start: str) -> None:
        """Signal that the clause starting with join_start should be a LATERAL one"""
        self._add_if_starts(self.lateral_joins, join_start)

    def _add_if_starts(self, target_set: Set[str], join_start: str):
        for a_join in self.joins:
            if a_join.startswith(join_start):
                target_set.add(a_join)

    def find_join(self, join_start: str) -> Tuple[str, int]:
        """Find a clause starting with join_start"""
        for idx, a_join in enumerate(self.joins):
            if a_join.startswith(join_start):
                return a_join, idx
        return "", -1

    def replace_in_join(self, idx: int, exp_from: str, exp_to: str):
        """Textual substitution in given join text"""
        self.joins[idx] = self.joins[idx].replace(exp_from, exp_to)

    def insert(self, a_join: str, idx: int):
        self.joins.insert(idx, a_join)


class WhereClause(object):
    """
    A 'where' clause in SQL. List of 'and' clauses.
    """

    __slots__ = ("ands",)

    def __init__(self) -> None:
        self.ands: List[str] = []

    def __mul__(self, other) -> "WhereClause":
        self.ands.append(other)
        return self

    def get_sql(self) -> str:
        if len(self.ands) > 0:
            return "\nWHERE " + "\n  AND ".join(self.ands)
        else:
            return " "

    # Not completely exact but good enough
    COL_RE = re.compile(r"\b(\w+)\.(\w+)\b", re.ASCII)

    def conds_and_refs(self) -> Generator[Tuple[str, Set[str]], None, None]:
        """
        Iterator over the conditions, with a pre-analysis on their references.
        """
        for a_cond in self.ands:
            refs = set([a_match.group(0) for a_match in self.COL_RE.finditer(a_cond)])
            yield a_cond, refs


class OrderClause(object):
    """
    An 'order by' clause in SQL. List of columns/aliases.
    """

    __slots__ = ("expressions", "columns", "window_start", "window_size")

    def __init__(self) -> None:
        self.expressions: List[str] = []
        self.columns: List[str] = []
        self.window_start = self.window_size = None

    def add_expression(
        self,
        alias: Optional[str],
        expr: str,
        asc_or_desc: Optional[str] = None,
        invert_nulls_first: bool = False,
    ) -> None:
        if asc_or_desc is None:
            asc_or_desc = "ASC"
        if invert_nulls_first:
            asc_or_desc += " NULLS FIRST" if asc_or_desc == "ASC" else " NULLS LAST"
        if alias is not None:
            # Refer to a table in select list
            self.expressions.append(f"{alias}.{expr} {asc_or_desc}")
            self.columns.append(alias + "." + expr)
        else:
            # Refer to a select expression
            self.expressions.append(f"{expr} {asc_or_desc}")
            self.columns.append(expr)

    def referenced_columns(self, with_prefices=True) -> Set[str]:
        if with_prefices:
            return set(self.columns)
        else:
            return set([a_col.split(".")[1] for a_col in self.columns])

    def set_window(self, start: Optional[int], size: Optional[int]) -> None:
        self.window_start: Optional[int] = start
        self.window_size: Optional[int] = size

    def get_sql(self) -> str:
        ret = (
            ("\nORDER BY " + ", ".join(self.expressions)) if self.expressions else "\n"
        )
        if self.window_start is not None:
            ret += f" OFFSET {self.window_start}"
        if self.window_size is not None:
            ret += f" LIMIT {self.window_size}"
        return ret

    def replace(self, chunk_from, chunk_to):
        self.expressions = [
            a_exp.replace(chunk_from, chunk_to) for a_exp in self.expressions
        ]
        self.columns = [a_col.replace(chunk_from, chunk_to) for a_col in self.columns]

    def clone(self) -> "OrderClause":
        ret = OrderClause()
        ret.expressions = self.expressions[:]
        ret.columns = self.columns[:]
        return ret
