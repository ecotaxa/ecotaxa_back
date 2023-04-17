# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A computation inside a dataset, defined textually and depending on free columns.
#
import math
from collections import OrderedDict
from typing import Dict, List, Any, Optional, Tuple, OrderedDict as OrderedDictT

from BO.ProjectVars import ProjectVar
from BO.Vocabulary import Term


class ComputedVar(ProjectVar):
    """
    E.g. individual_concentration = 1 / subsample_coef / total_water_volume
      or individual_biovolume = individual_volume / subsample_coef / total_water_volume
    The variables inside will be defined at project level, but it's not managed here.
    """

    def __init__(self, var_formula: str, term: Term, unit: Term):
        super().__init__(var_formula, term, unit)
        self.expanded_formula: Optional[str] = None
        self.references: OrderedDictT[str, str] = OrderedDict()

    def expand_extract_refs(
        self,
        defs: Dict[str, str],
        valid_prefixes: List[str],
        names_and_defs: Dict[str, str],
    ):
        """
        Expand the formula using given inside-variables definitions and get references, checking they are allowed.
        """
        formula = self.formula
        # Substitute known variables inside
        vars_in_exp = self.find_vars(formula)
        for a_var in vars_in_exp:
            if a_var in defs:
                a_subexp = defs[a_var]
                formula = formula.replace(a_var, "(" + a_subexp + ")")
        # Do an inventory of references inside the expanded expression
        vars_in_exp2 = self.find_vars(formula)
        for a_var in vars_in_exp2:
            if a_var in names_and_defs:
                self.references[a_var] = names_and_defs[a_var]
            elif a_var.startswith("math."):
                continue
            elif "." not in a_var:
                raise Exception(
                    "Expression '%s' is invalid (no dot) or unresolved from variables, found in expression '%s'"
                    % (a_var, formula)
                )
            else:
                prfx, free_col = a_var.split(".")
                if prfx not in valid_prefixes:
                    raise Exception(
                        "Variable '%s' does not start with valid suffix '%s', found in expression '%s'"
                        % (a_var, prfx, formula)
                    )
                self.references[a_var] = ""
        # Recompile. TODO: Not so elegant
        self.expanded_formula = formula
        self.code = compile(formula, "<formula>", "eval")

    def _is_bad_input(self, row: Dict[str, Any]) -> bool:
        try:
            for a_var in self.references.keys():
                float(row[a_var])
        except ValueError:
            return True
        return False

    def eval(self, row: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Evaluate self, using given dict as variable source.
        NaN is returned in 2 cases:
        - There was a NaN in input variables. 'R' does the same, it's OK-ish.
        - There was a bad input, e.g. a string which cannot be converted to float or a DB NULL.
        """
        try:
            dyn_val = eval(self.code, {"math": math}, row)
            return dyn_val, False
        except (TypeError, ValueError):
            nan_due_to_bad_input = self._is_bad_input(row)
            return math.nan, nan_due_to_bad_input
        except (
            NameError
        ):  # this 'should not' happen, but during dev, the raise below allows to set a breakpoint
            raise

    def replace_python_refs_with_SQL(
        self, replacements: Dict[Tuple[str, str], Tuple[str, str]]
    ):
        """
        Replace the references in expanded_formula formula & recompile.
        E.g. we can have sam.tot_vol in formula, but this is 'obj.member' python syntax which will
        fail during eval() as there is no 'obj'. So let it become sam_tot_vol.
        E.g. replacements contains {('sam','tot_vol'):('sam','t05')}
        """
        assert self.expanded_formula
        formula = self.expanded_formula
        for a_py_ref, a_sql_ref in replacements.items():
            # Replace e.g. sam.tot_vol/1000 -> sam_tot_vol/1000
            old_ref, new_ref = "%s.%s" % a_py_ref, "%s_%s" % a_py_ref
            if a_sql_ref[1][0] == "t":
                # e.g. t01 -> string
                formula = formula.replace(old_ref, "float(%s)" % new_ref)
            else:
                formula = formula.replace(old_ref, new_ref)
            # Remove old reference
            del self.references[old_ref]
            # Remember the SQL equivalent, as the row will arrive with this structure
            self.references[new_ref] = "%s.%s" % a_sql_ref
        self.expanded_formula = formula
        self.code = compile(formula, "<formula>", "eval")
