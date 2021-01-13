# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Base class for response models, in the idea we'll use them for large responses.
#
import typing

from pydantic import BaseModel

try:
    import orjson


    def json_dumps(v, *, default, option=0, return_bytes=False):
        params = {"default": default}
        if option > 0:
            params["option"] = option
        result = orjson.dumps(v, **params)
        if return_bytes is False:
            result = result.decode()
        if typing.TYPE_CHECKING and return_bytes is True:
            result = typing.cast(str, result)
        return result


    json_loads = orjson.loads
except ImportError:
    from json import loads as json_loads
    from json import dumps as json_dumps  # type:ignore


class ResponseModel(BaseModel):
    """
        Tuned model for faster serialization out.
        TODO: A bit useless in the context as FastAPI does _not_ use ser/deser from the model.
              Instead, it produces what needs to be sent over the wire and calls a JSON encoder onto it.
              So 1) It calls def jsonable_encoder (in FastAPI encoders.py)
                 2) It calls an encoder (presently ORJSONEncoder in main.py)
    """

    class Config:
        json_loads = json_loads
        json_dumps = json_dumps
