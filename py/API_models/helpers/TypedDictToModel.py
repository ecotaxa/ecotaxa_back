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
from typing import Type, Optional

from pydantic import BaseModel, create_model

from typing_extensions import TypedDict


def parse_typed_dict(typed_dict):
    annotations = {}
    for name, field in typed_dict.__annotations__.items():
        if field == Optional[str]:
            annotations[name] = (field, None)
        else:
            raise Exception("Not managed yet")

    ret = create_model(typed_dict.__name__, **annotations)
    # Make the model get-able
    ret.get = lambda self, k, d: getattr(self, k, d)
    return ret
