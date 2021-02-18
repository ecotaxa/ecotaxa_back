# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# An Object as seen by the user, i.e. the fields regarless of their storage.
# An Object cannot exist outside of a project due to "free" columns.
#
# The set comprises all objects from a Project, except the ones filtered by a set of criteria.
#
from abc import ABCMeta
from collections import OrderedDict
# starting 3.7
# from typing import OrderedDict as OrderedDictT
from typing import Any, List, Callable

from BO.Mappings import TableMapping, ProjectMapping
from DB import Project
from DB.helpers.ORM import Session
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class MappedEntity(metaclass=ABCMeta):
    """
        A mapped entity is included in a project, and shows DB columns possibly differently amongst projects.
    """
    FREE_COLUMNS_ATTRIBUTE: str
    """ Which field/attribute in the subclass contains the DB entity with mapped values """
    PROJECT_ACCESSOR: Callable[[Any], Project]
    """ How to reach the project containing the mapping """
    MAPPING_IN_PROJECT: str
    """ Where in the @See ProjectMapping class are the specific to the subclass """

    def __init__(self, session: Session):
        self._session = session
        # Extension
        self.free_columns: Any = OrderedDict()

    def exists(self):
        return getattr(self, self.FREE_COLUMNS_ATTRIBUTE) is not None

    def map_free_columns(self, mappings: TableMapping):
        free_cols = self.free_columns
        free_cols_data = getattr(self, self.FREE_COLUMNS_ATTRIBUTE)
        for a_tsv_col, a_real_col in mappings.tsv_cols_to_real.items():
            free_cols[a_tsv_col] = getattr(free_cols_data, a_real_col)

    @classmethod
    def get_free_fields(cls, mapped: Any,  # TODO: Should be 'MappedEntity'
                        field_list: List[str],
                        field_types: List[Any],
                        field_absent_vals: List[Any]) -> List[Any]:
        """
            Get free fields _values_ for the mapped entity, inside the project
            :param field_list: The names of the free columns for which value is returned
            :param field_types: The basic types e.g. int or float. Used as converters/verifiers e.g: float()
            :param field_absent_vals: The values used as marker for 'absent'. 'nan' for float.
        """
        assert len(field_list) == len(field_types) == len(field_absent_vals)
        mapping = ProjectMapping().load_from_project(cls.PROJECT_ACCESSOR(mapped))
        real_cols = getattr(mapping, cls.MAPPING_IN_PROJECT).find_tsv_cols(field_list)
        if len(real_cols) != len(field_list):
            raise TypeError("at least one of %s free column is absent" % field_list)
        # OK we have the real columns, get the values
        vals = [getattr(mapped, real_col) for real_col in real_cols]
        ret = []
        errs = []
        for a_field, a_val, a_type, an_absent_val in zip(field_list, vals, field_types, field_absent_vals):
            try:
                # convert (cast) to target type
                a_val = a_type(a_val)
            except TypeError:
                errs.append("%s (bad %s)" % (a_field, a_val))
                continue
            if a_val == an_absent_val:
                # emit an error if absent special value is seen
                errs.append("%s (abs %s)" % (a_field, an_absent_val))
                continue
            if a_type == float and float(a_val) == float("nan"):
                errs.append("%s (NaN)" % a_field)
                continue
            ret.append(a_val)
        if len(errs) > 0:
            raise TypeError(",".join(errs))
        return ret
