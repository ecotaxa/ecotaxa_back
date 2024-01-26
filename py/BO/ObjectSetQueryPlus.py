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
from pathlib import Path
from typing import (
    List,
    Optional,
    Tuple,
    Dict,
    Generator,
    Any,
    Iterable,
    Callable,
    Final,
)

from BO.Classification import ClassifIDT
from BO.ComputedVar import ComputedVar
from BO.ObjectSet import DescribedObjectSet
from BO.Vocabulary import Term
from DB.helpers.Direct import text
from DB.helpers.ORM import Session, Row
from DB.helpers.SQL import OrderClause, SQLParamDict, SelectClause
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

# To avoid saturating memory for large datasets, use a generator
# each .next() will yield a dict with similar structure, i.e. dict keys.
RowSourceT = Generator[Dict[str, Any], None, None]
# A typing for both in-mem list of dicts and row sources
IterableRowsT = Iterable[Dict[str, Any]]
# From:To and remove if no "To", i.e. if "To" is None
TaxoRemappingT = Dict[ClassifIDT, Optional[ClassifIDT]]
TaxoRemappingWith0AsNoneT = Dict[ClassifIDT, ClassifIDT]


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
    BY_SUBSAMPLE_AND_TAXO = BY_TAXO + BY_SUBSAMPLE
    BY_SAMPLE_SUBSAMPLE_AND_TAXO = BY_TAXO + BY_SUBSAMPLE + BY_SAMPLE
    BY_SAMPLE_AND_SUBSAMPLE = BY_SUBSAMPLE + BY_SAMPLE
    BY_PROJECT_AND_TAXO = (
        BY_TAXO + BY_SUBSAMPLE + BY_SAMPLE + BY_PROJECT
    )  # One day, for Collections

    @classmethod
    def without_taxo(cls, val: "ResultGrouping") -> "ResultGrouping":
        return val & ~cls.BY_TAXO  # type:ignore


class ObjectSetQueryPlus(object):
    """ """

    COUNT_STAR = "COUNT(*)"
    TAXONOMY_PK = "txo.id"
    SAMPLE_PK = "sam.sampleid"
    SUBSAMPLE_PK = "acq.acquisid"
    # The namings, from _formulae_ point of view
    SAMPLE_PREFIX = "sam"
    SUBSAMPLE_PREFIX = "ssm"
    OBJECT_PREFIX = "obj"
    KNOWN_PREFIXES: Final = [SAMPLE_PREFIX, SUBSAMPLE_PREFIX, OBJECT_PREFIX]

    def __init__(self, obj_set: DescribedObjectSet):
        self.obj_set = obj_set
        # Input data tweaking
        self.taxo_mapping: TaxoRemappingT = {}
        # Computations settings
        self.formulae: Dict[str, str] = {}
        #
        self.sql_select_list: List[str] = []  # What is needed
        self.defs_to_alias: Dict[str, str] = {}  # How it will appear
        self.grouping: ResultGrouping = ResultGrouping.NO_GROUPING  # The grouping
        self.sum_exp: Optional[ComputedVar] = None  # A complex aggregate

    def set_grouping(self, grouping: ResultGrouping) -> "ObjectSetQueryPlus":
        """
        Group results at this level.
        """
        assert (
            grouping & ResultGrouping.BY_PROJECT != ResultGrouping.BY_PROJECT
        ), "Single project for now"
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
        assert False, "one of %s is needed in select list, for grouping" % str(prfxs)

    def set_aliases(self, aliases: Dict[str, str]) -> "ObjectSetQueryPlus":
        """
        The result will have these as header columns.
        """
        self.defs_to_alias.update(aliases)
        return self

    def remap_categories(self, taxo_mappings: TaxoRemappingT) -> "ObjectSetQueryPlus":
        """
        The result will not contain any category in keys, only the ones in values.
        If a value is None then it's discarded.
        """
        self.taxo_mapping = taxo_mappings
        return self

    def set_formulae(self, formulae: Dict[str, str]) -> "ObjectSetQueryPlus":
        """
        Set the formulae, i.e. the way to extract significant values from free columns.
        """
        self.formulae = formulae
        return self

    def add_selects(self, cols_list: List[str]) -> "ObjectSetQueryPlus":
        """
        Augment what is needed as output.
        """
        self.sql_select_list.extend(cols_list)
        return self

    def _resolve_refs(
        self, aliases: Dict[str, str]
    ) -> Dict[Tuple[str, str], Tuple[str, str]]:
        """
        Resolve references, e.g. sam.tot_vol -> sam.t05. The prefixes are valid.
        As this is meant to complement ObjectSet queries, we use SQL table aliases from there.
        TODO: As we're here, it would be nice to include plain non-free columns as well.
        """
        assert self.sum_exp
        ret: Dict[Tuple[str, str], Tuple[str, str]] = {}
        mapping = self.obj_set.mapping
        for a_var in self.sum_exp.references.keys():
            if a_var in aliases:
                continue
            prfx, free_col = a_var.split(".")
            real_col, real_tbl = None, None
            if prfx == self.SAMPLE_PREFIX:
                # Sample, straightforward
                real_col = mapping.sample_mappings.tsv_cols_to_real.get(free_col)
                real_tbl = "sam"  # TODO: Use a constant from ObjectSet
            elif prfx == self.SUBSAMPLE_PREFIX:
                # Subsample, i.e. either Process or Acquisition but not both
                real_col1 = mapping.process_mappings.tsv_cols_to_real.get(free_col)
                real_col2 = mapping.acquisition_mappings.tsv_cols_to_real.get(free_col)
                if real_col1 is not None and real_col2 is not None:
                    raise Exception(
                        "%s.%s is ambiguous, as %s is present in both Process and Acquisition free columns"
                        % (prfx, free_col, free_col)
                    )
                elif real_col1 is not None:
                    real_col = real_col1
                    real_tbl = "prc"  # TODO: Use a constant from ObjectSet
                elif real_col2 is not None:
                    real_col = real_col2
                    real_tbl = "acq"  # TODO: Use a constant from ObjectSet
            elif prfx == self.OBJECT_PREFIX:
                real_col = mapping.object_mappings.tsv_cols_to_real.get(free_col)
                real_tbl = "obf"  # TODO: Use a constant from ObjectSet
            if real_col is None:
                raise Exception(
                    "Could not resolve %s.%s in project free columns" % (prfx, free_col)
                )
            assert real_tbl
            ret[(prfx, free_col)] = (real_tbl, real_col)
        return ret

    def aggregate_with_computed_sum(
        self, sum_expression: str, term: Term, unit: Term
    ) -> "ObjectSetQueryPlus":
        """
        Add a computed (i.e. from formula) sum to the query, with given name, for each grouping.
        """
        # Validate & compile straight away
        self.sum_exp = ComputedVar(sum_expression, term, unit)
        # Allow to reference a SQL output in the formula, not itself of course
        aliases_to_def = {
            an_alias: a_def
            for (a_def, an_alias) in self.defs_to_alias.items()
            if a_def != sum_expression
        }
        self.sum_exp.expand_extract_refs(
            self.formulae, self.KNOWN_PREFIXES, aliases_to_def
        )
        # Resolve references
        resolved = self._resolve_refs(aliases_to_def)
        self.sum_exp.replace_python_refs_with_SQL(resolved)
        return self

    def _group_by_columns(self) -> List[str]:
        """
            The list of columns implied by the required grouping, in hierarchical order.
        :return:
        """
        ret = []
        if self.grouping & ResultGrouping.BY_SAMPLE:
            ret.append(self.SAMPLE_PK)
        if self.grouping & ResultGrouping.BY_SUBSAMPLE:
            ret.append(self.SUBSAMPLE_PK)
        if self.grouping & ResultGrouping.BY_TAXO:
            ret.append(self.TAXONOMY_PK)
        return ret

    def _compute_group_by(self) -> str:
        grouping = " GROUP BY " + ", ".join(self._group_by_columns())
        if self.sum_exp:
            if self.COUNT_STAR in self.sum_exp.references.values():
                # The expression relies on SQL grouping
                return grouping
            # We can't have PG doing these aggregates as they are computed here in python
            return ""
        return grouping

    def _add_tech_selects(self, select: SelectClause) -> None:
        """
        Add the selected columns implied/needed by expression expansion.
        e.g. sam.t07 AS sam_tot_vol, acq.t03 AS ssm_sub_part
        """
        if self.sum_exp:
            aggreg_in_exp = self.COUNT_STAR in self.sum_exp.references.values()
            for a_py_ref, a_sql_ref in self.sum_exp.references.items():
                if aggreg_in_exp and a_sql_ref != self.COUNT_STAR:
                    select.add("MAX(" + a_sql_ref + ")", a_py_ref)
                else:
                    select.add(a_sql_ref, a_py_ref)
            for key_num, a_col in enumerate(self._group_by_columns()):
                select.add(a_col, "key%d" % key_num)

    def get_sql(self) -> Tuple[str, SQLParamDict]:
        """
        Compose the query and return it.
        """
        # Build SL, aliased parts if relevant
        select = self._selects_4_output()
        # Add implied selects
        self._add_tech_selects(select)
        select_clause = select.get_sql()
        # Group by
        group_clause = self._compute_group_by()
        #
        order_clause = OrderClause()
        if not self.sum_exp:
            # Order by all selected columns, in their given order
            for alias in select.aliases:
                order_clause.add_expression(alias=None, expr=alias)
        else:
            # Order by the grouping keys, in their order.
            # It's important as we detect the breaks in composite key to emit rows with aggregates.
            for key_col in self._group_by_columns():
                order_clause.add_expression(alias=None, expr=key_col)

        # Base SQL comes from filters
        from_, where, params = self.obj_set.get_sql(order_clause, select_clause)
        if len(self.taxo_mapping) > 0:
            select_clause = self._amend_query_for_mapping(from_, select_clause)
        sql = (
            select_clause
            + " FROM "
            + from_.get_sql()
            + where.get_sql()
            + group_clause
            + order_clause.get_sql()
        )
        return sql, params

    def _amend_query_for_mapping(self, from_, select_clause: str) -> str:
        """
        From parts of the ObjectSet SQL, inject the needed mapping, with a CTE.
        """
        pairs = []
        all_null: bool = True
        for from_txo, to_txo in self.taxo_mapping.items():
            all_null = all_null and to_txo is None
            to_val = "NULL" if (to_txo is None or to_txo == 0) else str(to_txo)
            pairs.append("(%d,%s)" % (from_txo, to_val))
        # PG needs a type if there is no value at all
        if all_null:
            pairs[-1] = pairs[-1][:-1] + "::int)"
        cte_txt = "WITH mpg (src_id, dst_id)" + " AS (VALUES " + ",".join(pairs) + ") "
        txo_join, idx = from_.find_join("taxonomy txo")
        # Read: when there was no mapping then lookup using classif_id else pick lookup even if null
        exp = "CASE WHEN mpg.src_id IS NULL THEN obh.classif_id ELSE mpg.dst_id END "
        from_.replace_in_join(idx, "obh.classif_id", exp)
        from_.insert("mpg ON mpg.src_id = obh.classif_id", idx)
        from_.set_outer("mpg ")
        select_clause = cte_txt + select_clause
        return select_clause

    def get_row_source(
        self, ro_session: Session, wrn_fct: Optional[Callable[[str], None]] = None
    ) -> RowSourceT:
        """
        Build a generator to loop over query results, eventually enriched.
        """
        # Data side
        sql, params = self.get_sql()
        logger.info("Execute SQL : %s", sql)
        logger.info("Params : %s", params)
        res = ro_session.execute(text(sql), params)
        if self.sum_exp is None:
            # Pure SQL, emit each row
            for a_simple_row in res.mappings():
                yield dict(a_simple_row)
        else:
            assert self.grouping != ResultGrouping.NO_GROUPING
            # Expression evaluation
            # Prepare a maximum of things outside the loop, which can be over hundreds of thousands of rows.
            eval_bnd = self.sum_exp.eval  # This is a bounded call
            dest_col = self.defs_to_alias[self.sum_exp.formula]
            # We have 3 parts in each row:
            #  - The output values for the TSV, one of them is "0" and will receive the formula result
            #  - The variables, input for formula evaluation
            #  - The numerical keys for grouping
            # e.g.: SELECT sam.orig_id AS sampleid, txo.display_name AS taxonid, 0 AS concentration,
            #              sam.t07 AS sam_tot_vol, acq.t03 AS ssm_sub_part,
            #              sam.sampleid AS key0, txo.id AS key1 FROM obj_head obh
            out_vars = self._selects_4_output().aliases
            nb_out_vars = len(out_vars)
            formula_vars = list(self.sum_exp.references.keys())
            keys_idx = nb_out_vars + len(formula_vars)
            # Init loop vars 'previous' states
            vals_sum: float = 0.0
            last_row: Optional[Row] = None
            last_keys: Tuple = tuple()
            a_row: Row
            for a_row in res:
                vars_row = dict(zip(formula_vars, a_row[nb_out_vars:]))
                val, nan_because_bad = eval_bnd(vars_row)
                if val != val:  # NaN test
                    if nan_because_bad:
                        wrn_msg = (
                            "Some values could not be converted to float in %s"
                            % str(dict(vars_row))
                        )
                        if wrn_fct is not None:
                            wrn_fct(wrn_msg)
                keys = tuple(a_row[keys_idx:])
                if last_row is None:
                    # Ye olde first row problem...
                    last_keys = keys
                elif keys != last_keys:
                    # Emit a row
                    out_row = dict(zip(out_vars, last_row))
                    out_row[dest_col] = vals_sum
                    last_keys = keys
                    vals_sum = 0.0
                    yield out_row
                last_row = a_row
                vals_sum += val
            if last_row is not None:
                # The antique last row corner
                out_row = dict(zip(out_vars, last_row))
                out_row[dest_col] = vals_sum
                yield out_row

    def get_result(
        self, ro_session: Session, wrn_fct: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Read the row source, in full, and return it.
        """
        src = self.get_row_source(ro_session, wrn_fct)
        return [a_row for a_row in src]

    def write_result_to_csv(
        self,
        ro_session: Session,
        file_path: Path,
        wrn_fct: Optional[Callable[[str], None]],
    ) -> int:
        """
        Write all from row source into CSV.
        """
        nb_lines = self.write_row_source_to_csv(
            self.get_row_source(ro_session, wrn_fct), file_path
        )
        return nb_lines

    def _selects_4_output(self) -> SelectClause:
        """
        Compute the selected expressions which will become TSV columns.
        """
        ret = SelectClause()
        sels = self.sql_select_list[:]
        for a_sel in sels:
            alias = self.defs_to_alias[a_sel]
            ret.add(a_sel, alias)
        # Add a placeholder for sum_expression
        if self.sum_exp is not None:
            ret.add("0", self.defs_to_alias[self.sum_exp.formula])
        return ret

    def _get_header(self) -> List[str]:
        """
        Return the CSV header from SQL column.
        """
        return self._selects_4_output().aliases

    def write_row_source_to_csv(self, res: IterableRowsT, out_file: Path) -> int:
        """
        Write many rows, from mem or cursor, into the output file.
        """
        nb_lines = 0
        with open(out_file, "w") as csv_file:
            col_names = self._get_header()
            wtr = csv.DictWriter(
                csv_file, col_names, delimiter="\t", quotechar='"', lineterminator="\n"
            )
            wtr.writeheader()
            for a_row in res:
                # There is a nice sanity check here, that all rows have the structure defined in the header
                wtr.writerow(a_row)
                nb_lines += 1
        return nb_lines
