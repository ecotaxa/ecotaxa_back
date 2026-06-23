# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible a Pydantic model from typed dictionary
#
# https://github.com/samuelcolvin/pydantic/issues/760
#
from typing import Optional, Dict, Any, Type

from pydantic import create_model, ConfigDict, Field

from API_models.helpers import PydanticModelT
from helpers.pydantic import PydanticDescriptionT


def typed_dict_to_model(
    typed_dict_class: Type, pydantic_descrip: PydanticDescriptionT
) -> PydanticModelT:
    annotations: Dict[str, Any] = {}
    descrips = pydantic_descrip.get_fields()
    for name, field in typed_dict_class.__annotations__.items():
        if field == Optional[str]:
            field_info = descrips[name]
            # Create a new FieldInfo with default=None, copying other properties
            new_field_info = Field(
                default=None,
                title=field_info.title,
                description=field_info.description,
                examples=field_info.examples,
            )
            annotations[name] = (field, new_field_info)
        else:
            # app doesn't even start if below is raised -> nocover
            raise Exception("Not managed yet")  # pragma:nocover

    config = ConfigDict(
        coerce_numbers_to_str=True, from_attributes=True, populate_by_name=True
    )
    ret: PydanticModelT = create_model(
        typed_dict_class.__name__, __config__=config, **annotations
    )

    return ret
