# -*- coding: utf-8 -*-
# noinspection PyUnresolvedReferences
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# SQLAlchemy core imports, for re-export. If you don't need the ORM, querying using below primitives is much faster.
#
from typing import List

# noinspection PyUnresolvedReferences
from sqlalchemy.sql import select, Select, delete, Delete, update, Update


def get_bundle_columns(stmt: Select, index: int) -> List[str]:
    """
    Extract column keys from a bundle in a statement, at given index.
    """
    bundle = stmt.column_descriptions[index]["expr"]
    return [col.key for col in bundle.c]
