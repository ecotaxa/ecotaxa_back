# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# Generic SQL composer from an ObjectSet, with augmented capabilities:
#   - Remapping of read taxonomy.
#   - Addition of python formulae as virtual columns.
#
import csv
import enum
import math
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Generator, Any, Iterable

from BO.Classification import ClassifIDT
from BO.ObjectSet import DescribedObjectSet
from BO.ProjectVars import ProjectVar
from BO.User import UserIDT
from BO.Vocabulary import Units, Vocabulary
from DB import Taxonomy
from DB.helpers.Direct import text
from DB.helpers.ORM import Session
from DB.helpers.SQL import OrderClause, SQLParamDict
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

# To avoid saturating memory for large datasets, use a generator
# each .next() will yield a dict with similar structure, i.e. dict keys.
RowSourceT = Generator[Dict[str, Any], None, None]
# A typing for both in-mem list of dicts and row sources
IterableRowsT = Iterable[Dict[str, Any]]
# From, To
TaxoRemappingT = Dict[ClassifIDT, ClassifIDT]


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
    """

    """
    COUNT_STAR = "COUNT(*)"
    TAXONOMY_PK = "txo.id"
    SAMPLE_PK = "sam.sampleid"
    SUBSAMPLE_PK = "acq.acquisid"
    KNOWN_PREFICES = ['sam', 'ssm', 'obj']

    def __init__(self, obj_set: DescribedObjectSet, user_id: UserIDT):
        self.obj_set = obj_set
        self.user_id = user_id
        self.prj_id = obj_set.prj_id
        # Input data tweaking
        self.taxo_mapping: TaxoRemappingT = {}
        # Computations settings
        self.formulae: Dict[str, str] = {}
        #
        self.sql_select_list: List[str] = []  # What is needed
        self.aliases: Dict[str, str] = {}  # How it will appear
        self.grouping: ResultGrouping = ResultGrouping.NO_GROUPING  # The grouping
        self.count: bool = False  # A simple aggregate
        self.sum_exp: Optional[str] = None  # A complex aggregate

    def set_grouping(self, grouping: ResultGrouping) -> 'ObjectSetQueryPlus':
        """
            Group results at this level.
        """
        assert grouping != ResultGrouping.BY_PROJECT_AND_TAXO, "Single project for now"
        # Sanity check, we cannot group if no data from grouping level
        if grouping & ResultGrouping.BY_TAXO:
            self._check_select_contains("txo.")
        if grouping & ResultGrouping.BY_SUBSAMPLE:
            self._check_select_contains("acq.", "prc.")
        if grouping & ResultGrouping.BY_SAMPLE:
            self._check_select_contains("sam.")
        self.grouping = grouping
        return self

    def _check_select_contains(self, prfx1: str, prfx2: Optional[str] = None) -> None:
        prfxs = [prfx1] + ([prfx2] if prfx2 else [])
        for a_prefix in prfxs:
            for a_col in self.sql_select_list:
                if a_prefix in a_col:
                    return
        assert False, "one of %s in needed for grouping" % str(prfxs)

    def set_aliases(self, aliases: Dict[str, str]):
        """
            The result will have these as header columns.
        """
        self.aliases.update(aliases)

    def remap_categories(self, taxo_mappings: TaxoRemappingT):
        """
            The result will not contain any category in keys, only the ones in values.
        """
        self.taxo_mapping = taxo_mappings

    def set_formulae(self, formulae: Dict[str, str]):
        """
            Set the formulae, i.e. the way to extract significant values from free columns.
        """
        self.formulae = formulae

    def add_select(self, cols_list: List[str], before: bool = True) -> 'ObjectSetQueryPlus':
        """
            Augment what is needed as output.
        """
        if before:
            self.sql_select_list[:0] = cols_list
        else:
            self.sql_select_list.extend(cols_list)
        return self

    def aggregate_with_count(self) -> 'ObjectSetQueryPlus':
        """
            Add a count to the query, for each grouping.
        """
        assert self.grouping != ResultGrouping.NO_GROUPING
        assert self.sum_exp is None
        self.count = True
        return self

    def aggregate_with_computed_sum(self, sum_expression: str) -> 'ObjectSetQueryPlus':
        """
            Add a computed sum to the query, with given name, for each grouping.
        """
        assert self.grouping != ResultGrouping.NO_GROUPING
        assert not self.count
        self.sum_exp = sum_expression
        return self

    def _compute_group_by(self) -> str:
        if self.sum_exp:
            # We can't have PG doing these sums as they are computed here in python
            return ""
        ret = []
        if self.grouping & ResultGrouping.BY_TAXO:
            ret.append(self.TAXONOMY_PK)
        if self.grouping & ResultGrouping.BY_SUBSAMPLE:
            ret.append(self.SUBSAMPLE_PK)
        if self.grouping & ResultGrouping.BY_SAMPLE:
            ret.append(self.SAMPLE_PK)
        return " GROUP BY " + ", ".join(ret)

    def get_sql(self) -> Tuple[str, SQLParamDict]:
        """
            Compose the query and return it.
        """
        sels = self._get_selects()
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
        group_clause = self._compute_group_by()
        # Order by all selected columns, in their given order
        order_clause = OrderClause()
        for a_sel in sels:
            alias_or_plain = self.aliases.get(a_sel, a_sel)
            order_clause.add_expression(alias=None, expr=alias_or_plain)

        # Base SQL comes from filters
        from_, where, params = self.obj_set.get_sql(self.user_id, order_clause, select_clause)
        sql = select_clause + " FROM " + from_.get_sql() + where.get_sql() + group_clause + order_clause.get_sql()
        return sql, params

    def _eval_from_exp_and_formulae(self) -> ProjectVar:
        """
            Return an eval-able python code chunk.
            TODO: Absent values e.g. 9999999
        """
        sum_exp = self.sum_exp
        assert sum_exp
        # Substitute known variables inside
        vars_in_exp = ProjectVar.find_vars(sum_exp)
        for a_var in vars_in_exp:
            if a_var in self.formulae:
                a_subexp = self.formulae[a_var]
                sum_exp = sum_exp.replace(a_var, "(" + a_subexp + ")")
        # Transform dot notations into single var e.g. sam.tot_vol -> sam_tot_vol
        vars_in_exp2 = ProjectVar.find_vars(sum_exp)
        for a_var in vars_in_exp2:
            if a_var.startswith("math."):  # TODO: more libs?
                continue
            elif "." not in a_var:
                raise Exception("Could not expand variable '%s' found in expression '%s'" % (a_var, self.sum_exp))
            else:
                prfx, free_col = a_var.split(".")
                if prfx not in self.KNOWN_PREFICES:
                    raise Exception("Variable '%s' does not start with valid suffix '%s', found in expression '%s'" %
                                    (a_var, prfx, self.sum_exp))
                # TODO: resolve free col
                sum_exp = sum_exp.replace(a_var, prfx + "_" + free_col)

        # TODO: This is wrong!
        prj_var = ProjectVar(sum_exp, Vocabulary.volume_sampled, Units.cubic_metres)
        return prj_var

    def get_row_source(self, ro_session: Session) -> RowSourceT:
        """
            Build a generator to loop over query results, eventually enriched.
        """
        # Data side
        sql, params = self.get_sql()
        logger.info("Execute SQL : %s", sql)
        logger.info("Params : %s", params)
        res = ro_session.execute(text(sql), params)
        # Scientific side
        sum_eval = None
        dest_col = None
        if self.sum_exp is not None:
            sum_eval = self._eval_from_exp_and_formulae()
            dest_col = self.aliases[self.sum_exp]
        for a_row in res:
            db_row = dict(a_row)
            if dest_col is not None:
                assert sum_eval
                dyn_val = eval(sum_eval.code, {"math": math}, db_row)
                if not sum_eval.is_valid(dyn_val):
                    raise TypeError("Not valid %s: %s" % (sum_eval.formula, str(dyn_val)))
                db_row[dest_col] = dyn_val
            yield db_row

    def get_result(self, ro_session: Session) -> List[Dict[str, Any]]:
        """
            Read the row source, in full, and return it.
        """
        src = self.get_row_source(ro_session)
        return [a_row for a_row in src]

    def write_result_to_csv(self, ro_session: Session, file_path: Path) -> int:
        """
            Write row source into CSV.
        """
        nb_lines = self.write_row_source_to_csv(self.get_row_source(ro_session), file_path)
        return nb_lines

    def _get_selects(self) -> List[str]:
        """
            Get user selects.
        """
        ret = self.sql_select_list[:]
        # Include count
        if self.count:
            ret += [self.COUNT_STAR]
        return ret

    def _get_header(self) -> List[str]:
        """
            Return the CSV header from SQL column.
        """
        ret = []
        for a_col in self._get_selects():
            if a_col in self.aliases:
                ret.append(self.aliases[a_col])
            else:
                raise Exception("expression '%s' is not aliased" % a_col)
        if self.sum_exp is not None:
            ret.append(self.aliases[self.sum_exp])
        return ret

    def write_row_source_to_csv(self, res: IterableRowsT, out_file: Path) -> int:
        """
            Write many rows, from mem or cursor, into the output file.
        """
        nb_lines = 0
        with open(out_file, 'w') as csv_file:
            col_names = self._get_header()
            wtr = csv.DictWriter(csv_file, col_names, delimiter='\t', quotechar='"', lineterminator='\n')
            wtr.writeheader()
            for a_row in res:
                # There is a nice sanity check here, that all rows have the structure defined in the header
                wtr.writerow(a_row)
                nb_lines += 1
        return nb_lines


class PerTaxonResultsQuery(ObjectSetQueryPlus):
    """
        A specialized ObjectSetQueryPlus which always groups result, at least, by a Taxonomy table column.
    """

    def __init__(self, obj_set: DescribedObjectSet, user_id: UserIDT, txo_col: str):
        super().__init__(obj_set, user_id)
        assert txo_col.startswith("txo.")
        assert txo_col[4:] in Taxonomy.__dict__
        self.sql_select_list = [txo_col]
        self.set_grouping(ResultGrouping.BY_TAXO)
