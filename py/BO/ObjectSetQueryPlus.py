# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# Generic SQL composer from an ObjectSet, with augmented capabilities:
#   - Remapping of read taxonomy.
#   - Addition of python formulae as virtual columns.
#
import enum
from typing import List, Optional, Tuple, Dict

from BO.ObjectSet import DescribedObjectSet
from BO.User import UserIDT
from DB import Taxonomy
from DB.helpers.SQL import OrderClause, SQLParamDict


class ResultGrouping(enum.IntEnum):
    """
        How to group results.
    """
    NO_GROUPING = 0  # Return individual rows
    BY_TAXO = 1  # Aggregates are per taxo
    BY_SAMPLE = 2  # Aggregates are per sample
    BY_SUBSAMPLE = 4  # Aggregates are per subsample
    BY_PROJECT = 8  # Aggregates are per project
    BY_SAMPLE_AND_TAXO = BY_TAXO + BY_SAMPLE
    BY_SUBSAMPLE_AND_TAXO = BY_TAXO + BY_SUBSAMPLE + BY_SAMPLE
    BY_PROJECT_AND_TAXO = BY_TAXO + BY_SUBSAMPLE + BY_SAMPLE + BY_PROJECT  # One day, for Collections


class ObjectSetQueryPlus(object):

    def __init__(self, obj_set: DescribedObjectSet, user_id: UserIDT):
        self.obj_set = obj_set
        self.user_id = user_id
        self.prj_id = obj_set.prj_id
        #
        self.grouping: ResultGrouping = ResultGrouping.NO_GROUPING
        self.sql_select_list: List[str] = []
        self.aliases: Dict[str, str] = {}
        self.count: Optional[str] = None

    def set_grouping(self, grouping: ResultGrouping) -> 'ObjectSetQueryPlus':
        """
            Group results at this level.
        """
        assert grouping != ResultGrouping.BY_PROJECT_AND_TAXO, "Single project for now"
        # Sanity check, we cannot group if no data from grouping level
        if grouping & ResultGrouping.BY_TAXO:
            self.check_select("txo.")
        if grouping & ResultGrouping.BY_SUBSAMPLE:
            self.check_select("acq.", "prc.")
        if grouping & ResultGrouping.BY_SAMPLE:
            self.check_select("sam.")
        self.grouping = grouping
        return self

    def check_select(self, prfx1: str, prfx2: Optional[str] = None) -> None:
        prfxs = [prfx1]
        if prfx2:
            prfxs.append(prfx2)
        for a_prefix in prfxs:
            for a_col in self.sql_select_list:
                if a_prefix in a_col:
                    return
        assert False, "one of %s in needed for grouping" % str(prfxs)

    def set_select(self, cols_list: List[str]) -> 'ObjectSetQueryPlus':
        """
            What is needed as output.
        """
        self.sql_select_list = cols_list
        return self

    def add_aliases(self, aliases: Dict[str, str]):
        """
            The result will have these are header columns.
        """
        self.aliases.update(aliases)

    def add_select(self, cols_list: List[str], before: bool = True) -> 'ObjectSetQueryPlus':
        """
            Augment what is needed as output.
        """
        if before:
            self.sql_select_list[:0] = cols_list
        else:
            self.sql_select_list.extend(cols_list)
        return self

    def select_count(self, count_alias: str) -> 'ObjectSetQueryPlus':
        """
            Add a count to the query, with given name, for each grouping.
        """
        assert self.grouping != ResultGrouping.NO_GROUPING
        self.count = count_alias
        self.aliases["COUNT(*)"] = count_alias
        return self

    def _compute_group_by(self) -> List[str]:
        ret = []
        if self.grouping & ResultGrouping.BY_TAXO:
            ret.append("txo.id")
        if self.grouping & ResultGrouping.BY_SUBSAMPLE:
            ret.append("acq.acquisid")
        if self.grouping & ResultGrouping.BY_SAMPLE:
            ret.append("sam.sampleid")
        return ret

    def get_sql(self) -> Tuple[str, SQLParamDict]:
        """
            Compose the query and return it.
        """
        sels = self.sql_select_list
        # Include count
        if self.count is not None:
            sels.append("COUNT(*)")
        # Build SL, aliased parts if relevant
        aliased_sels = []
        for a_sel in sels:
            als = self.aliases.get(a_sel)
            if als is None:
                aliased_sels.append(a_sel)
            else:
                aliased_sels.append(a_sel + " AS " + als)
        select_clause = "SELECT " + ", ".join(aliased_sels)
        # Group by
        group_clause = " GROUP BY " + ", ".join(self._compute_group_by())
        # Order by
        order_clause = OrderClause()
        for a_sel in sels:
            alias_or_plain = self.aliases.get(a_sel, a_sel)
            order_clause.add_expression(alias=None, expr=alias_or_plain)

        # Base SQL comes from filters
        from_, where, params = self.obj_set.get_sql(self.user_id, order_clause, select_clause)
        sql = select_clause + " FROM " + from_.get_sql() + where.get_sql() + group_clause + order_clause.get_sql()
        return sql, params


class PerTaxonResultsQuery(ObjectSetQueryPlus):
    """
        A specialized ObjectSetQueryPlus which always groups result, at least, by a Taxonomy table column.
    """

    def __init__(self, obj_set: DescribedObjectSet, user_id: UserIDT, txo_col: str):
        super().__init__(obj_set, user_id)
        assert txo_col in Taxonomy.__dict__
        self.set_select(["txo." + txo_col]).set_grouping(ResultGrouping.BY_TAXO)
