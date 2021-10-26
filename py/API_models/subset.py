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


class GroupDefinitions(str, Enum):
    categories = "C"
    samples = "S"
    acquisitions = "A"


class SubsetReq(BaseModel):
    """ Subset request. """
    filters: Dict[str, str] = Field(title="Filters", description="The filters to apply to project.", default={},
                                    example={"freenum": "n01", "freenumst": "0"})
    dest_prj_id: int = Field(title="Destination project id", description="The destination project ID.", example=22)
    group_type: GroupDefinitions = Field(title="Group type",
                                         description="Define the groups in which to apply limits. "
                                                     "C for categories, S for samples, A for acquisitions.",
                                         example=GroupDefinitions.acquisitions)
    limit_type: LimitMethods = Field(title="Limit type",
                                     description="The type of limit_value: P for %, V for constant, both per group.",
                                     example=LimitMethods.percent)
    limit_value: float = Field(title="Limit value",
                               description="Limit value, e.g. 20% or 5 per copepoda or 5% per sample.", example=10.0)

    class Config:
        schema_extra = {"title": "Subset request Model"}


class SubsetRsp(BaseModel):
    """ Subset response. """
    job_id: int = Field(title="Job Id", description="The job created for this operation.", example=143)
    # errors: List[str] = Field(title="The errors found during processing",
    #                           default=[])
