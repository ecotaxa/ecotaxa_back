# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Pydantic model from dataclass
#
import dataclasses
import datetime
from typing import Optional, TypeVar, Dict, List
# noinspection PyUnresolvedReferences
from typing import _GenericAlias  # type: ignore

from pydantic import create_model, BaseConfig
from pydantic.fields import ModelField

from API_models.helpers import PydanticModelT


class DataclassConfig(BaseConfig):
    pass


# Generify the def with input type
T = TypeVar('T')


def dataclass_to_model(clazz: T, add_suffix: bool = False, titles: Optional[Dict[str, str]] = None) -> PydanticModelT:
    model_fields = {}
    a_field: dataclasses.Field
    for a_field in dataclasses.fields(clazz):
        fld_type = a_field.type
        default = None  # TODO
        if fld_type in (str, Optional[str], int, float, datetime.datetime):
            # Basic types become directly model fields
            pass
        elif type(fld_type) == _GenericAlias:
            # A typing e.g. typing.List[BO.UserBO]
            str_type = str(fld_type)
            if str_type.startswith("typing.List["):
                # TODO: I did not find how to instrospect a type from typings, so below is a bit ugly
                contained_class_full_name = str_type[12:-1]
                try:
                    to_import, contained_class_name = contained_class_full_name.rsplit(".", 1)
                    globs: Dict = {}
                    exec("import " + to_import, globs)
                    contained_class = eval(contained_class_full_name, globs)
                    fld_type = List[dataclass_to_model(contained_class)] # type: ignore
                except ValueError:
                    pass
            # Pydantic maps everything to object, no doc or fields or types
            pass
        else:
            raise Exception("Not managed yet :", fld_type)  # pragma:nocover
        model_fields[a_field.name] = (fld_type, default)
    model_name = clazz.__name__ + ("Model" if add_suffix else "")  # type: ignore
    ret: PydanticModelT = create_model(
        model_name, __config__=DataclassConfig, **model_fields  # type: ignore
    )
    if titles is not None:
        # Amend with title, for doc. Let crash (KeyError) if titles are not up-to-date with base.
        for a_field_name, a_title in titles.items():
            the_field: ModelField = ret.__fields__[a_field_name]
            the_field.field_info.title = a_title
    return ret
