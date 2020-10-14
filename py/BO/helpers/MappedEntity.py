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
from typing import Any

from BO.Mappings import TableMapping
from DB.helpers.ORM import Session
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class MappedEntity(metaclass=ABCMeta):
    """
        A mapped entity is included in a project, and shows DB columns possibly differently amongst projects.
    """
    FREE_COLUMNS_ATTRIBUTE: str

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
