# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Pydantic model from dataclass
#
import datetime
from typing import Optional, TypeVar

import dataclasses
from pydantic import create_model, BaseConfig

from API_models.helpers import PydanticModelT


class DataclassConfig(BaseConfig):
    pass


# Generify the def with input type
T = TypeVar('T')


def dataclass_to_model(clazz: T) -> PydanticModelT:
    model_fields = {}
    a_field: dataclasses.Field
    for a_field in dataclasses.fields(clazz):
        if a_field.type in (str, Optional[str], int, float, datetime.datetime):
            model_fields[a_field.name] = (a_field.type, None)
        else:
            # app doesn't even start if below is raised -> nocover
            raise Exception("Not managed yet :", a_field.type)  # pragma:nocover
    ret = create_model(
        clazz.__name__, __config__=DataclassConfig, **model_fields  # type: ignore
    )
    return ret
