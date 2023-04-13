# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible the DB model into CRUD objects.
#
from typing import Dict, Any

from sqlalchemy import inspect
from sqlalchemy.orm import ColumnProperty

from API_models.helpers import PydanticModelT
from DB.helpers.ORM import ModelT
from helpers.pydantic import BaseConfig, create_model


class OrmConfig(BaseConfig):
    orm_mode = True


def combine_models(db_model: ModelT,
                   pydantic_model: PydanticModelT) -> PydanticModelT:
    """
        Combine DB model with a plain Pydantic one. The result is a new model with _only_ fields
        from the pydantic, but types, nullity and default values from DB.
        -> Fields missing in pydantic model are not in result.
        The resulting model class in conventionally the pydantic's one removing first char.
    """
    fields: Dict[str, Any] = {}
    not_null_cols = set()
    # Pydantic fields
    pydantic_fields = pydantic_model.__fields__
    pydantic_fields_names = set(pydantic_fields.keys())
    # Build model from ORM fields
    mapper = inspect(db_model)
    assert mapper is not None
    for attr in mapper.attrs:
        if not isinstance(attr, ColumnProperty):
            # Exclude e.g. relationships
            continue
        if not attr.columns:
            continue
        column = attr.columns[0]
        python_type = column.type.python_type
        name = attr.key
        if name not in pydantic_fields_names:
            continue
        default = None
        if column.default is None and not column.nullable:
            default = ...
        if not column.nullable:
            not_null_cols.add(name)
        fields[name] = (python_type, default)
    ret: PydanticModelT = create_model(
        pydantic_model.__name__[1:], __config__=OrmConfig, **fields
    )
    # Copy field information from the Pydantic model
    for a_field_name, a_field in pydantic_fields.items():
        ret_field = ret.__fields__[a_field_name]
        ret_field.field_info = a_field.field_info
    # Set required for not null columns
    for a_not_null_col in not_null_cols:
        ret.__fields__[a_not_null_col].required = True
    return ret
