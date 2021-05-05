# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import Dict

from helpers.pydantic import BaseModel, Field


class LimitMethods(str, Enum):
    percent = "P"
    constant = "V"


class SubsetReq(BaseModel):
    """ Subset request. """
    filters: Dict[str, str] = Field(title="The filters to apply to project", default={})
    dest_prj_id: int = Field(title="The destination project ID.")
    limit_type: LimitMethods = Field(title="The type of limit_value: P for %, V for constant, both per category.")
    limit_value: float = Field(title="Limit value, e.g. 20% or 5 per copepoda.")
    do_images: bool = Field(title="If set, also clone images.")


class SubsetRsp(BaseModel):
    """ Subset response. """
    job_id: int = Field(title="The job created for this operation.")
    # errors: List[str] = Field(title="The errors found during processing",
    #                           default=[])
