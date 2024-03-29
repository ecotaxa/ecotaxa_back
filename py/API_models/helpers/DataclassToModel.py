# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Pydantic model from dataclass
#
import dataclasses
import datetime
from typing import Optional, Dict, List, Type, Any

# noinspection PyUnresolvedReferences,PyProtectedMember
from typing import _GenericAlias  # type: ignore

# noinspection PyPackageRequirements
from pydantic import create_model

from API_models.helpers import PydanticModelT
from BO.User import MinimalUserBO, UserActivity
from helpers.pydantic import PydanticDescriptionT


# noinspection PyPackageRequirements


def dataclass_to_model_with_suffix(
    data_class: Type, pydantic_class: Optional[PydanticDescriptionT] = None
) -> PydanticModelT:
    """
    Return a model from dataclass, the name of the produced model is dataclass' one + "Model"
    """
    return dataclass_to_model(data_class, pydantic_class, True)


def dataclass_to_model(
    data_class: Type,
    pydantic_class: Optional[PydanticDescriptionT] = None,
    add_suffix: bool = False,
) -> PydanticModelT:
    model_fields: Dict[str, Any] = {}
    a_field: dataclasses.Field
    for a_field in dataclasses.fields(data_class):
        fld_type = a_field.type
        default = None  # TODO
        if fld_type in (str, Optional[str], int, float, datetime.datetime):
            # Basic types become directly model fields
            pass
        elif fld_type == list:  # WIP
            # Compiled (by mypyc) classes have no type info
            if "_ids" in a_field.name or "counts" in a_field.name:
                fld_type = List[int]
            elif "column" in a_field.name:
                fld_type = List[int]
            elif "variances" in a_field.name:
                fld_type = List[Optional[float]]
            elif "annotators" in a_field.name:
                fld_type = List[MinimalUserBO]
            elif "activities" in a_field.name:
                fld_type = List[UserActivity]
            elif "used_taxa" in a_field.name:
                fld_type = List[int]
            else:
                raise Exception("Not managed yet :", fld_type, a_field.name)
        elif type(fld_type) == _GenericAlias:
            # A typing e.g. typing.List[BO.UserBO]
            str_type = str(fld_type)
            if str_type.startswith("typing.List["):
                # TODO: I did not find how to introspect a type from typings, so below is a bit ugly
                contained_class_full_name = str_type[12:-1]
                try:
                    to_import, contained_class_name = contained_class_full_name.rsplit(
                        ".", 1
                    )
                    globs: Dict = {}
                    exec("import " + to_import, globs)
                    if contained_class_full_name == "typing.Union[float, NoneType]":
                        fld_type = List[Optional[float]]
                    else:
                        try:
                            contained_class = eval(contained_class_full_name, globs)
                        except NameError:
                            raise
                        fld_type = List[dataclass_to_model(contained_class)]  # type: ignore
                except ValueError:
                    pass
            # Pydantic maps everything to object, no doc or fields or types
            pass
        else:
            raise Exception(
                "Not managed yet :", fld_type, a_field.name
            )  # pragma:nocover
        model_fields[a_field.name] = (fld_type, default)
    model_name = data_class.__name__ + ("Model" if add_suffix else "")
    ret: PydanticModelT = create_model(model_name, **model_fields)
    # Inject an iterator into the dataclass
    # As when converting a plain object to a Model, pydantic tries to call dict(obj).
    #   See in pydantic/main.py
    #   @classmethod
    #   def validate(cls: Type['Model'], value: Any) -> 'Model':
    setattr(
        data_class,
        "__iter__",
        lambda self: iter([(fld, getattr(self, fld)) for fld in model_fields.keys()]),
    )
    if pydantic_class is not None:
        # Amend with Field() calls, for doc. Let crash (KeyError) if desync with base.
        for a_field_name, a_field_desc in pydantic_class.__fields__.items():
            the_desc_field = ret.__fields__[a_field_name]
            the_desc_field.field_info = a_field_desc.field_info
    return ret
