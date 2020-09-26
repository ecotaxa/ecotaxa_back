# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible the DB model into CRUD objects.
#
from typing import Type, TypeVar

from sqlalchemy import inspect
from sqlalchemy.orm import ColumnProperty

from API_models.helpers import PydanticModelT
from helpers.pydantic import BaseConfig, create_model


class OrmConfig(BaseConfig):
    orm_mode = True


# Generify the def with input type
T = TypeVar('T')


def sqlalchemy_to_pydantic(db_model: T, *,
                           config: Type[BaseConfig] = OrmConfig,
                           exclude=None) -> PydanticModelT:
    if exclude is None:
        exclude = []
    fields = {}
    # Build model from ORM fields
    mapper = inspect(db_model)
    for attr in mapper.attrs:
        if isinstance(attr, ColumnProperty):
            if attr.columns:
                column = attr.columns[0]
                python_type = column.type.python_type
                name = attr.key
                if name in exclude:
                    continue
                default = None
                if column.default is None and not column.nullable:
                    default = ...
                fields[name] = (python_type, default)
    pydantic_model = create_model(
        db_model.__name__ + "Model", __config__=config, **fields  # type: ignore
    )
    return pydantic_model
