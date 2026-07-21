# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

# noinspection PyUnresolvedReferences,PyPackageRequirements
from typing import List, Any, Optional, Dict, Type

# Just to avoid tagging every "pydantic" reference in PyCharm, as pydantic is included in FastAPI
# noinspection PyUnresolvedReferences
from pydantic import (
    BaseConfig,
    BaseModel,
    Field,
    create_model,
    root_validator,
    dataclasses,
    validator,
)


class DescriptiveModel(BaseModel):
    """Just fields descriptions, these models can be combined
    with various containers to be sent across the wire."""

    class Config:
        arbitrary_types_allowed = (
            True  # We don't check that classes inside models are models themselves
        )


PydanticDescriptionT = Type[DescriptiveModel]


def sort_and_prune(
    a_list: List[Any],
    order_field: Optional[str],
    model_cols: Dict[str, Any],
) -> List[Any]:
    """
    Sort a_list by order_field. Pagination (window_start/window_size) is applied
    in SQL upstream, on the ID query, before results are built - not here, so
    that we never fetch and enrich more rows than will actually be returned.
    This only needs to sort in Python for order_field values that aren't plain
    DB columns (SQL already sorted a_list for the ones that are, so re-sorting
    here is a harmless no-op for those).
    """
    if order_field is not None:
        reverse = False
        if order_field[0] == "-":
            order_field = order_field[1:]
            reverse = True
        if order_field in model_cols:
            default_if_none = model_cols[order_field]
            sort_lambda = lambda elem: (
                getattr(elem, order_field)
                if getattr(elem, order_field)
                else default_if_none
            )
            a_list.sort(key=sort_lambda, reverse=reverse)
    return a_list
