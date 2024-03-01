# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# Primitives for doing operations on a mapped table/rows
#
import abc
from abc import ABCMeta
from typing import Dict, List

from BO.ColumnUpdate import ColUpdateList, ColUpdate
from BO.Mappings import MappedTableTypeT, ProjectMapping
from DB import Session, Query
from DB.Project import Project
from DB.helpers.ORM import non_key_cols, ModelT


class MappedTable(metaclass=ABCMeta):
    """
    A mapped table is included in a project, and shows DB columns possibly differently amongst projects.
    """

    def __init__(self, session: Session):
        self.session = session

    @abc.abstractmethod
    def add_filter(self, upd: Query) -> Query:
        ...  # pragma:nocover

    def _apply_on_all(
        self, clazz: MappedTableTypeT, project: Project, updates: List[ColUpdate]
    ) -> int:
        """
        Apply all updates on all impacted rows by their ID.
        """
        prj_mappings = ProjectMapping().load_from_project(project)
        tbl_mappings = prj_mappings.by_table[clazz].tsv_cols_to_real
        clean_updates = self._sanitize_updates(clazz, tbl_mappings, updates)
        # Eventually there is nothing left after filtering
        if len(clean_updates) == 0:
            return 0
        return self._do_updates(clazz, clean_updates)

    def _apply_on_all_non_mapped(self, clazz: ModelT, updates: List[ColUpdate]) -> int:
        """
        Apply all updates on all impacted rows by their ID, for non-mapped clazz.
        """
        clean_updates = self._sanitize_updates(clazz, {}, updates)
        return self._do_updates(clazz, clean_updates)

    @staticmethod
    def _sanitize_updates(
        clazz: ModelT, tbl_mappings: Dict[str, str], updates: List[ColUpdate]
    ) -> List[ColUpdate]:
        """
        Ensure that the update will do the job, avoiding e.g. non-existing columns.
        Also does the free columns mapping, if required.
        """
        clean_updates = []
        a_col_upd: ColUpdate
        updatable_cols = non_key_cols(clazz)
        for a_col_upd in updates:
            # We need a real DB column or a mapped one
            col_to_upd = a_col_upd["ucol"]
            if col_to_upd in tbl_mappings:
                a_col_upd["ucol"] = tbl_mappings[col_to_upd]
            elif col_to_upd not in updatable_cols:
                # Ignored with no reporting
                continue
            clean_updates.append(a_col_upd)
        return clean_updates

    def _do_updates(self, clazz: ModelT, updates: List[ColUpdate]) -> int:
        # OK we have a set of col+values to apply to a set of entities
        if len(updates) == 0:
            # Eventually there is nothing left after filtering
            return 0
        upd = self.session.query(clazz)
        upd = self.add_filter(upd)
        affected_rows = upd.update(
            values=ColUpdateList(updates).as_dict_for_db(), synchronize_session=False
        )
        self.session.commit()
        return affected_rows
