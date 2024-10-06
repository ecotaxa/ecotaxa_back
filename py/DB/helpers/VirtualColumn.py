# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2024  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

import functools
from typing import Callable, List, Any, Dict
from typing import TYPE_CHECKING

from DB.helpers import Result
from DB.helpers.Postgres import find_in_cursor


class VirtualColumn(object):
    """For SQL statements, replace a former normal column in a SELECT with a computation"""

    name: str = ""  # How it should appear client_side
    filler: Callable  # How to compute the value from full SQLA model, is a @staticmethod in the model
    sql: str = ""

    @staticmethod
    def result_to_py(from_sel: Any) -> Any:
        """Convert output from SELECT into python equivalent. Default to 'what does DBAPI is fine'"""
        return from_sel


# TODO: Remove when py3.9+
if TYPE_CHECKING:
    VirtualColumnSetT = Dict[str, VirtualColumn]
    from mypy.plugins.default import partial
else:
    VirtualColumnSetT = dict
    partial = Any


class VirtualColumnSet(VirtualColumnSetT):
    def __init__(self, *args):
        super().__init__({an_arg.name: an_arg for an_arg in args})

    def sql_for(self, name: str):
        return self[name].sql + " AS " + name

    @staticmethod
    def replace_in_rs(trsf: Callable, idx: int, data: List[Any]) -> None:
        data[idx] = trsf(data[idx])

    def get_transformers(self, res: Result, offset_to_data: int) -> List[partial]:
        col_descs = res.cursor.description  # type:ignore # case5
        ret = []
        vc: VirtualColumn
        for name, vc in self.items():
            idx = find_in_cursor(col_descs, vc.name)
            if idx > 0:
                ret.append(
                    functools.partial(
                        VirtualColumnSet.replace_in_rs,
                        vc.result_to_py,
                        idx - offset_to_data,
                    )
                )
        return ret

    def add_to_model(self, model: Any) -> Any:
        for name, vc in self.items():
            setattr(model, name, vc.filler(model))
        return model
