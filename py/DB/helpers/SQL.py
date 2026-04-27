# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A bit of SQL encapsulation.
#
import re
from collections import OrderedDict
from decimal import Decimal
from typing import Union, List, Dict, Optional, Set, Generator, Tuple, Any

# A dict for sending parametrized SQL to the engine
SQLParamDict = Dict[str, Union[int, float, Decimal, str, List[int], List[str]]]

# Not completely exact but good enough
COL_RE = re.compile(r"\b(\w+)\.(\w+)\b", re.ASCII)
IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$", re.ASCII)


class SelectClause(object):
    """
    List of selected expressions, eventually aliased.
    """

    __slots__ = ("expressions", "aliases")

    def __init__(self):
        self.expressions: List[str] = []
        self.aliases: List[Optional[str]] = []

    def clone(self) -> "SelectClause":
        new_clause = SelectClause()
        new_clause.expressions = list(self.expressions)
        new_clause.aliases = list(self.aliases)
        return new_clause

    def add_expr(self, expr: str, alias: Optional[str] = None) -> "SelectClause":
        assert isinstance(expr, str), repr(expr)
        self.expressions.append(expr)
        self.aliases.append(alias)
        return self

    def get_sql(self) -> str:
        aliased = []
        for expr, alias in zip(self.expressions, self.aliases):
            if alias:
                if IDENTIFIER_RE.match(alias):
                    aliased.append(f"{expr} AS {alias}")
                else:
                    aliased.append(f'{expr} AS "{alias}"')
            else:
                aliased.append(expr)
        ret = "SELECT " + ", ".join(aliased)
        return ret

    def table_refs(self) -> Set[str]:
        """Return e.g. obh, obj, img, etc... depending on selected values"""
        refs = set()
        for expr in self.expressions:
            for match in COL_RE.finditer(expr):
                refs.add(match.group(1))
        return refs

    def _remove_items(self, indices: List[int]):
        for i in sorted(indices, reverse=True):
            del self.expressions[i]
            del self.aliases[i]

    @staticmethod
    def transfer(
        from_clause: "SelectClause", to_clause: "SelectClause", for_table_ref: str
    ):
        indices_to_move = []
        for i, expr in enumerate(from_clause.expressions):
            # Find refs in this expression
            refs = {match.group(1) for match in COL_RE.finditer(expr)}
            if for_table_ref in refs:
                indices_to_move.append(i)
        # Move items
        for i in indices_to_move:
            to_clause.add_expr(from_clause.expressions[i], from_clause.aliases[i])
        from_clause._remove_items(indices_to_move)

    def replace_alias(self, table_alias: str, replace_alias: str) -> "SelectClause":
        for i, expr in enumerate(self.expressions):
            # Mutate table_alias. prefix if present
            self.expressions[i] = expr.replace(f"{table_alias}.", f"{replace_alias}.")
        return self

    def remove_for_table_alias(self, table_alias: str):
        indices_to_remove = []
        for i, expr in enumerate(self.expressions):
            # Find refs in this expression
            refs = {match.group(1) for match in COL_RE.finditer(expr)}
            if table_alias in refs:
                indices_to_remove.append(i)
        self._remove_items(indices_to_remove)

    def remove_for_column_alias(self, col_alias: str):
        indices_to_remove = [
            i for i, alias in enumerate(self.aliases) if alias == col_alias
        ]
        self._remove_items(indices_to_remove)


class AliasedSelectClause(SelectClause):
    """
    SelectClause for which all aliases are mandatory.
    """

    def __init__(self):
        SelectClause.__init__(self)
        self.aliases: List[str]

    def add_expr(
        self, expr: str, alias: str
    ) -> "AliasedSelectClause":  # type:ignore[override]
        assert alias is not None, "Alias is mandatory for AliasedSelectClause"
        SelectClause.add_expr(self, expr, alias)
        return self


class FromClause(object):
    """
    A 'from' clause in SQL. List of joined table expressions.
    """

    __slots__ = ("joins", "left_joins", "lateral_joins", "table_aliases")

    def __init__(self, first: str):
        self.joins: List[str] = [first]
        self.left_joins: Set[int] = set()
        self.lateral_joins: Set[int] = set()
        self.table_aliases: OrderedDict[str, int] = OrderedDict()
        self._add_alias(first)

    def _add_alias(self, expression: str, idx: Optional[int] = None):
        if idx is None:
            idx = len(self.joins) - 1
        assert idx is not None
        # 1. Look for AS alias
        match = re.search(r"\s+AS\s+([a-zA-Z0-9_]+)", expression, re.IGNORECASE)
        if match:
            self.table_aliases[match.group(1)] = idx
            return
        # 2. Look for alias ON
        match = re.search(r"\s+([a-zA-Z0-9_]+)\s+ON\b", expression, re.IGNORECASE)
        if match:
            self.table_aliases[match.group(1)] = idx
            return
        # 3. Fallback: take the last part
        parts = expression.split()
        if parts:
            last_part = parts[-1].strip("()")
            if "(" in last_part:
                last_part = last_part.split("(")[0]
            self.table_aliases[last_part] = idx

    def __add__(self, other) -> "FromClause":
        self.joins.append(other)
        self._add_alias(other)
        return self

    def get_sql(self) -> str:
        sqls = [self.joins[0]]
        for i, a_join in enumerate(self.joins[1:], start=1):
            lateral = "LATERAL " if i in self.lateral_joins else ""
            if i in self.left_joins:
                sqls.append("LEFT JOIN " + lateral + a_join)
            else:
                sqls.append("JOIN " + lateral + a_join)
        return "\n ".join(sqls)

    def remove_if_refers_to(self, table_name: str) -> None:
        indices_to_remove = [
            i for i, a_join in enumerate(self.joins) if table_name in a_join
        ]
        # Iterating in reverse to remove indices correctly
        for i in sorted(indices_to_remove, reverse=True):
            if i in self.left_joins:
                self.left_joins.remove(i)
            if i in self.lateral_joins:
                self.lateral_joins.remove(i)
            # Adjust indices
            self.left_joins = {
                idx if idx < i else idx - 1 for idx in self.left_joins if idx != i
            }
            self.lateral_joins = {
                idx if idx < i else idx - 1 for idx in self.lateral_joins if idx != i
            }
            del self.joins[i]
            # Update aliases
            self.table_aliases = OrderedDict(
                (alias, (idx if idx < i else idx - 1))
                for alias, idx in self.table_aliases.items()
                if idx != i
            )

    def set_outer(self, join_start: str) -> "FromClause":
        """Signal that the clause starting with join_start should be a LEFT one"""
        self._add_if_starts(self.left_joins, join_start)
        return self

    def clear_outer(self, idx: int) -> "FromClause":
        if idx in self.left_joins:
            self.left_joins.remove(idx)
        return self

    def set_lateral(self, join_start: str) -> "FromClause":
        """Signal that the clause starting with join_start should be a LATERAL one"""
        self._add_if_starts(self.lateral_joins, join_start)
        return self

    def _add_if_starts(self, target_set: Set[int], join_start: str):
        for i, a_join in enumerate(self.joins):
            if a_join.startswith(join_start):
                target_set.add(i)

    def find_join(self, join_start: str) -> Tuple[str, int]:
        """Find a clause starting with join_start"""
        for idx, a_join in enumerate(self.joins):
            if a_join.startswith(join_start):
                return a_join, idx
        return "", -1

    def replace_in_join(self, idx: int, exp_from: str, exp_to: str):
        """Textual substitution in given join text"""
        self.joins[idx] = self.joins[idx].replace(exp_from, exp_to)

    def replace_table(self, table_from: str, table_to: str):
        """Textual substitution of a table name in all joins"""
        for i, a_join in enumerate(self.joins):
            if table_from in a_join:
                self.joins[i] = a_join.replace(table_from, table_to)
        # Rebuild table_aliases
        self.table_aliases = OrderedDict()
        for i, a_join in enumerate(self.joins):
            self._add_alias(a_join, i)

    def insert(self, a_join: str, idx: int):
        self.joins.insert(idx, a_join)
        # Shift indices in sets
        self.left_joins = {i if i < idx else i + 1 for i in self.left_joins}
        self.lateral_joins = {i if i < idx else i + 1 for i in self.lateral_joins}
        # Shift indices in aliases
        self.table_aliases = OrderedDict(
            (alias, (old_idx if old_idx < idx else old_idx + 1))
            for alias, old_idx in self.table_aliases.items()
        )
        # Add new alias
        self._add_alias(a_join, idx)

    def table_refs(self) -> List[str]:
        return list(self.table_aliases.keys())

    @staticmethod
    def transfer(
        from_clause: "FromClause", to_clause: "FromClause", for_table_ref: str
    ):
        indices_to_move = []
        # Identify the definition join
        if for_table_ref in from_clause.table_aliases:
            indices_to_move.append(from_clause.table_aliases[for_table_ref])
        # Move items
        for i in indices_to_move:
            join = from_clause.joins[i]
            to_clause.joins.append(join)
            # Handle lateral/left joins if needed
            new_idx = len(to_clause.joins) - 1
            if i in from_clause.left_joins:
                to_clause.left_joins.add(new_idx)
            if i in from_clause.lateral_joins:
                to_clause.lateral_joins.add(new_idx)
            # Add alias to to_clause
            to_clause._add_alias(join, new_idx)

        # Remove items from from_clause
        # Iterating in reverse to remove indices correctly
        for i in sorted(indices_to_move, reverse=True):
            if i in from_clause.left_joins:
                from_clause.left_joins.remove(i)
            if i in from_clause.lateral_joins:
                from_clause.lateral_joins.remove(i)
            # Adjust indices in sets
            from_clause.left_joins = {
                idx if idx < i else idx - 1 for idx in from_clause.left_joins
            }
            from_clause.lateral_joins = {
                idx if idx < i else idx - 1 for idx in from_clause.lateral_joins
            }
            del from_clause.joins[i]
            # Update aliases in from_clause
            from_clause.table_aliases = OrderedDict(
                (alias, (idx if idx < i else idx - 1))
                for alias, idx in from_clause.table_aliases.items()
                if idx != i
            )


class WhereClause(object):
    """
    A 'where' clause in SQL. List of 'and' clauses.
    """

    __slots__ = ("ands", "params")

    def __init__(self) -> None:
        self.ands: List[str] = []
        self.params: SQLParamDict = {}

    def __mul__(self, other) -> "WhereClause":
        self.ands.append(other)
        return self

    def chain(self, other) -> "WhereClause":
        self.ands.append(other)
        return self

    def add_param(self, name: str, value: Any) -> "WhereClause":
        self.params[name] = value
        return self

    def get_sql(self) -> str:
        if len(self.ands) > 0:
            return "\nWHERE " + "\n  AND ".join(self.ands)
        else:
            return " "

    def conds_and_refs(self) -> Generator[Tuple[str, Set[str]], None, None]:
        """
        Iterator over the conditions, with a pre-analysis on their references.
        """
        for a_cond in self.ands:
            refs = set([a_match.group(0) for a_match in COL_RE.finditer(a_cond)])
            yield a_cond, refs

    def clear(self):
        self.ands.clear()
        self.params.clear()


class OrderClause(object):
    """
    An 'order by' clause in SQL. List of columns/aliases.
    """

    __slots__ = ("expressions", "columns", "window_start", "window_size")

    def __init__(self) -> None:
        self.expressions: List[str] = []
        self.columns: List[str] = []
        self.window_start: Optional[int] = None
        self.window_size: Optional[int] = None

    def clone(self) -> "OrderClause":
        ret = OrderClause()
        ret.expressions = self.expressions[:]
        ret.columns = self.columns[:]
        return ret

    def add_expression(
        self,
        table_alias: Optional[str],
        expr: str,
        asc_or_desc: Optional[str] = None,
        invert_nulls_first: bool = False,
    ) -> "OrderClause":
        if asc_or_desc is None:
            asc_or_desc = "ASC"
        if invert_nulls_first:
            asc_or_desc += " NULLS FIRST" if asc_or_desc == "ASC" else " NULLS LAST"
        if table_alias is not None:
            # Refer to a table in select list
            self.expressions.append(f"{table_alias}.{expr} {asc_or_desc}")
            self.columns.append(table_alias + "." + expr)
        else:
            # Refer to a select expression
            self.expressions.append(f"{expr} {asc_or_desc}")
            self.columns.append(expr)
        return self

    def referenced_columns(self, with_prefices=True) -> Set[str]:
        if with_prefices:
            return set(self.columns)
        else:
            return set([a_col.split(".")[1] for a_col in self.columns])

    def table_refs(self) -> Set[str]:
        """Return e.g. obh, obj, img, etc... depending on ordered values"""
        refs = set()
        for expr in self.expressions:
            for match in COL_RE.finditer(expr):
                refs.add(match.group(1))
        return refs

    def set_window(self, start: Optional[int], size: Optional[int]) -> "OrderClause":
        self.window_start = start
        self.window_size = size
        return self

    def has_window(self) -> bool:
        return self.window_start is not None or self.window_size is not None

    def get_sql(self) -> str:
        ret = ("ORDER BY " + ", ".join(self.expressions)) if self.expressions else ""
        if self.window_start is not None:
            ret += f" OFFSET {self.window_start}"
        if self.window_size is not None:
            ret += f" LIMIT {self.window_size}"
        return ret

    def replace(self, chunk_from, chunk_to) -> "OrderClause":
        self.expressions = [
            a_exp.replace(chunk_from, chunk_to) for a_exp in self.expressions
        ]
        self.columns = [a_col.replace(chunk_from, chunk_to) for a_col in self.columns]
        return self
