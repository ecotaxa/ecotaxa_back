# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Attempt to map as automatically as possible the DB model into CRUD objects.
#
#
# Pydantic model from typed dictionary
#
# https://github.com/samuelcolvin/pydantic/issues/760
#
from typing import Optional, TypeVar, Dict, Any

# noinspection PyPackageRequirements
from pydantic import create_model

from API_models.helpers import PydanticModelT
# noinspection PyPackageRequirements
from pydantic.fields import ModelField

# Generify the def with input type
T = TypeVar('T')


def typed_dict_to_model(typed_dict: T, field_infos:  Optional[Dict[str, Any]] = None):  # TODO -> Type[BaseModel]:
    annotations = {}
    for name, field in typed_dict.__annotations__.items():
        if field == Optional[str]:
            annotations[name] = (field, None)
        else:
            # app doesn't even start if below is raised -> nocover
            raise Exception("Not managed yet")  # pragma:nocover

    ret: PydanticModelT = create_model(
        typed_dict.__name__, **annotations  # type: ignore
    )
    # Make the model get-able
    # noinspection PyTypeHints
    ret.get = lambda self, k, d: getattr(self, k, d)  # type: ignore

    if field_infos is not None:
        # Amend with Field() calls, for doc. Let crash (KeyError) if desync with base.
        for a_field_name, a_field_info in field_infos.items():
            the_desc_field: ModelField = ret.__fields__[a_field_name]
            the_desc_field.field_info = a_field_info
    return ret
