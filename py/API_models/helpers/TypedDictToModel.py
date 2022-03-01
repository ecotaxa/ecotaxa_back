# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible a Pydantic model from typed dictionary
#
# https://github.com/samuelcolvin/pydantic/issues/760
#
from typing import Optional, TypeVar, Dict, Any, Generic, Type, Union, Tuple

# noinspection PyPackageRequirements
from pydantic import create_model
# noinspection PyPackageRequirements
from pydantic.fields import ModelField
from pydantic.generics import GenericModel, GenericModelT

from API_models.helpers import PydanticModelT

# Generify the def with input type
T = TypeVar('T')
TDT = TypeVar('TDT')  # TypedDict type
CT = TypeVar('CT')  # Config Type


# Ref: https://pydantic-docs.helpmanual.io/usage/models/#generic-models
class TypedDict2Pydantic(GenericModel, Generic[TDT, CT]):
    def __class_getitem__(cls: Type[GenericModelT], params: Union[Type[Any], Tuple[Type[Any], ...]]) -> Type[Any]:
        dict_model, how = params  # type:ignore
        ret = _typed_dict_to_model(dict_model, field_infos=how.description)
        return ret


def _typed_dict_to_model(typed_dict: T,
                         field_infos: Optional[Dict[str, Any]] = None,
                         config: Any = None) -> PydanticModelT:
    annotations = {}
    for name, field in typed_dict.__annotations__.items():
        if field == Optional[str]:
            annotations[name] = (field, None)
        else:
            # app doesn't even start if below is raised -> nocover
            raise Exception("Not managed yet")  # pragma:nocover

    ret: PydanticModelT = create_model(
        typed_dict.__name__, __config__=config, **annotations  # type: ignore
    )

    if field_infos is not None:
        # Amend with Field() calls, for doc. Let crash (KeyError) if desync with base.
        for a_field_name, a_field_info in field_infos.items():
            the_desc_field: ModelField = ret.__fields__[a_field_name]
            the_desc_field.field_info = a_field_info
    return ret
