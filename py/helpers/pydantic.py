# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

# noinspection PyUnresolvedReferences,PyPackageRequirements
from typing import List, Any, Optional, Dict

# Just to avoid tagging every "pydantic" reference in PyCharm, as pydantic is included in FastAPI
# noinspection PyUnresolvedReferences
from pydantic import BaseConfig, BaseModel, Field, create_model, root_validator


def sort_and_prune(a_list: List[Any], order_field: Optional[str],
                   model_cols: Dict[str, Any],
                   window_start: Optional[int],
                   window_size: Optional[int]) -> List[Any]:
    if order_field is not None:
        reverse = False
        if order_field[0] == "-":
            order_field = order_field[1:]
            reverse = True
        if order_field in model_cols:
            default_if_none = model_cols[order_field]
            sort_lambda = lambda elem: getattr(elem, order_field) if getattr(elem, order_field) else default_if_none
            a_list.sort(key=sort_lambda, reverse=reverse)
    if window_start is not None:
        a_list = a_list[window_start:]
    if window_size is not None:
        a_list = a_list[:window_size]
    return a_list