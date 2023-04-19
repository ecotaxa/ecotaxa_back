# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible a Pydantic model from typed dictionary
#
# https://github.com/samuelcolvin/pydantic/issues/760
#
from typing import Optional, Dict, Any, Type

# noinspection PyPackageRequirements
from pydantic import create_model

from API_models.helpers import PydanticModelT
from helpers.pydantic import PydanticDescriptionT


# noinspection PyPackageRequirements


def typed_dict_to_model(
    typed_dict_class: Type, pydantic_class: PydanticDescriptionT
) -> PydanticModelT:
    annotations: Dict[str, Any] = {}
    for name, field in typed_dict_class.__annotations__.items():
        if field == Optional[str]:
            annotations[name] = (field, None)
        else:
            # app doesn't even start if below is raised -> nocover
            raise Exception("Not managed yet")  # pragma:nocover

    ret: PydanticModelT = create_model(
        typed_dict_class.__name__, __config__=pydantic_class.__config__, **annotations
    )

    # Amend with Field() calls, for doc. Let crash (KeyError) if desync with base.
    for a_field_name, a_field_desc in pydantic_class.__fields__.items():
        the_desc_field = ret.__fields__[a_field_name]
        the_desc_field.field_info = a_field_desc.field_info

    return ret
