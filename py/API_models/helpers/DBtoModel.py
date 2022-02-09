# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible the DB model into CRUD objects.
#
from typing import Type, TypeVar, Dict, Any, Generic, Union, Tuple

from pydantic.fields import ModelField
from sqlalchemy import inspect
from sqlalchemy.orm import ColumnProperty

from API_models.helpers import PydanticModelT
from helpers.pydantic import BaseConfig, create_model


class OrmConfig(BaseConfig):
    orm_mode = True


# Generify the def with input type
T = TypeVar('T')

from pydantic.generics import GenericModel, GenericModelT

DBT = TypeVar('DBT')  # TODO: Should be an SQLA model
CT = TypeVar('CT')


# Ref: https://pydantic-docs.helpmanual.io/usage/models/#generic-models
class SQLAlchemy2Pydantic(GenericModel, Generic[DBT, CT]):
    def __class_getitem__(cls: Type[GenericModelT], params: Union[Type[Any], Tuple[Type[Any], ...]]) -> Type[Any]:
        db_model, how = params  # type:ignore
        # TODO: Remove the 'exclude' completely. If no doc, not included.
        try:
            exclude = how.exclude
        except AttributeError:
            exclude = None
        ret = _sqlalchemy_to_pydantic(db_model, exclude=exclude, field_infos=how.description)
        return ret


def _sqlalchemy_to_pydantic(db_model: T, *,
                            config: Type[BaseConfig] = OrmConfig,
                            exclude=None,
                            field_infos: Dict[str, Any]) -> PydanticModelT:
    if exclude is None:
        exclude = []
    fields = {}
    not_null_cols = set()
    # Build model from ORM fields
    mapper = inspect(db_model)
    for attr in mapper.attrs:
        if not isinstance(attr, ColumnProperty):
            continue
        if not attr.columns:
            continue
        column = attr.columns[0]
        python_type = column.type.python_type
        name = attr.key
        if name not in field_infos.keys():
            continue
        default = None
        if column.default is None and not column.nullable:
            default = ...
        if not column.nullable:
            not_null_cols.add(name)
        fields[name] = (python_type, default)
    ret: PydanticModelT = create_model(
        db_model.__name__ + "Model", __config__=config, **fields  # type: ignore
    )
    # Add field info if available
    if field_infos is not None:
        # Amend with Field() calls, for doc. Let crash (KeyError) if desync with base.
        for a_field_name, a_field_info in field_infos.items():
            the_desc_field: ModelField = ret.__fields__[a_field_name]
            the_desc_field.field_info = a_field_info
    # Set required for not null columns
    for a_not_null_col in not_null_cols:
        ret.__fields__[a_not_null_col].required = True
    return ret
