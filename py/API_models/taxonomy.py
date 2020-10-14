# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Taxonomy API operations.
#
from typing import List

from pydantic import Field
from pydantic.main import BaseModel

from API_models.helpers.DBtoModel import OrmConfig


class TaxaSearchRsp(BaseModel):
    id: int = Field(title="The taxon/category IDs")
    text: str = Field(title="The taxon name, display one.")
    pr: int = Field(title="1 if the taxon is in project list, 0 otherwise.")


class TaxonModel(BaseModel):
    __config__ = OrmConfig
    id: int = Field(title="The taxon/category IDs")
    display_name: str = Field(title="The taxon/category full name")
    lineage: List[str] = Field(title="The taxon/category name of ancestors")
