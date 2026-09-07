# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible the DB model into CRUD objects.
#
from typing import Dict, Any, Optional

from pydantic_core import PydanticUndefined
from sqlalchemy import inspect as sqla_inspect
from sqlalchemy.orm import ColumnProperty

from API_models.helpers import PydanticModelT
from DB.helpers.ORM import ModelT
from helpers.pydantic import (
    ConfigDict,
    create_model,
    PydanticDescriptionT,
    FieldInfo,
)

OrmConfig = ConfigDict(from_attributes=True)


def combine_models(
    db_model: ModelT, pydantic_descrip: PydanticDescriptionT
) -> PydanticModelT:
    """
    Combine DB model with a plain Pydantic one. The result is a new model with _only_ fields
    from the pydantic, but types, nullity and default values from DB.
    -> Fields missing in pydantic model are not in result.
    The resulting model class in conventionally the pydantic's one removing first char.
    """
    fields: Dict[str, Any] = {}
    # Pydantic fields
    pydantic_fields = pydantic_descrip.get_fields()
    pydantic_fields_names = set(pydantic_fields.keys())
    # Build model from ORM fields
    mapper = sqla_inspect(db_model)
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
        field_info: FieldInfo = pydantic_fields[name]
        # https://docs.pydantic.dev/2.7/migration/#required-optional-and-nullable-fields
        if field_info.default != PydanticUndefined:
            # A default was provided in the description
            python_type = Optional[python_type]  # type: ignore[assignment]
        elif column.nullable:
            python_type = Optional[python_type]  # type: ignore[assignment]
            field_info = FieldInfo.merge_field_infos(field_info, default=None)
        elif column.default is not None and type(column.default) in (str, int, float):
            field_info = FieldInfo.merge_field_infos(field_info, default=column.default)
        fields[name] = (python_type, field_info)
    ret: PydanticModelT = create_model(
        pydantic_descrip.__name__[1:], __config__=OrmConfig, **fields
    )
    return ret
