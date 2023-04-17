# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Model introspection
#
from typing import Dict, Any

from API_models.helpers import PydanticModelT


def plain_columns(a_model: PydanticModelT) -> Dict[str, Any]:
    """
    Return the non-entity columns in given model, with a default value if None
    """
    ret = {}
    schema = a_model.schema()
    for a_col, its_desc in schema["properties"].items():
        fld_type = its_desc.get("type")
        if fld_type is None:
            continue
        if fld_type in ("string",):
            ret[a_col] = ""
        elif fld_type in ("integer", "boolean", "number"):
            ret[a_col] = "0"
    return ret
