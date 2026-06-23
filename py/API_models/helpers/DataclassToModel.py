# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Pydantic model from dataclass
#
import dataclasses
import datetime
import typing
from typing import Optional, Dict, List, Type, Any, Annotated
# noinspection PyUnresolvedReferences,PyProtectedMember
from typing import _GenericAlias  # type: ignore

# noinspection PyPackageRequirements
from pydantic import create_model

from API_models.helpers import PydanticModelT
from BO.User import MinimalUserBO, UserActivity
from helpers.pydantic import PydanticDescriptionT, FieldInfo

BASE_TYPES = (
    str,
    Optional[str],
    int,
    Optional[int],
    float,
    Optional[float],
    datetime.datetime,
    Optional[datetime.datetime],
)


def dataclass_to_model_with_suffix(
    data_class: Type, pydantic_descr: Optional[PydanticDescriptionT] = None
) -> PydanticModelT:
    """
    Return a model from dataclass, the name of the produced model is dataclass' one + "Model"
    """
    return dataclass_to_model(data_class, pydantic_descr, True)


def dataclass_to_model(
    data_class: Type,
    pydantic_descrip: Optional[PydanticDescriptionT] = None,
    add_suffix: bool = False,
) -> PydanticModelT:
    model_fields: Dict[str, Any] = {}
    if pydantic_descrip is not None:
        descrips = pydantic_descrip.get_fields()
    else:
        descrips = None
    a_field: dataclasses.Field
    try:
        fields = dataclasses.fields(data_class)
    except TypeError:
        raise Exception("Not a dataclass, check recursion:", data_class)
    for a_field in fields:
        fld_type = a_field.type
        default = None  # TODO
        if fld_type in BASE_TYPES:
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
            if typing.get_origin(fld_type) == list:
                (contained_class,) = typing.get_args(fld_type)
                if contained_class in BASE_TYPES:
                    fld_type = List[contained_class]  # type: ignore
                elif dataclasses.is_dataclass(contained_class):
                    fld_type = List[dataclass_to_model(contained_class)]  # type: ignore
                else:
                    raise Exception(
                        "Not list of unknown :", fld_type, contained_class
                    )  # pragma:nocover
            else:
                raise Exception(
                    "No complicated typing yet :", fld_type, a_field.name
                )  # pragma:nocover
        else:
            raise Exception(
                "Not managed yet :", fld_type, a_field.name
            )  # pragma:nocover
        if descrips is not None:
            field_info = descrips[a_field.name]
            field_info = FieldInfo.merge_field_infos(field_info, default=default)
        else:
            # No description, a title derived from field name will appear, e.g. "last_annot" -> "title":"Last Annot"
            field_info = FieldInfo(default=default)
        model_fields[a_field.name] = Annotated[fld_type, field_info]
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
    return ret
