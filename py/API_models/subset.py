# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum

from API_models.filters import ProjectFiltersDict
from helpers.pydantic import BaseModel, ConfigDict, Field


class LimitMethods(str, Enum):
    percent = "P"
    constant = "V"


class GroupDefinitions(str, Enum):
    categories = "C"
    samples = "S"
    acquisitions = "A"
    internal_ids = "I"


class SubsetReq(BaseModel):
    """Subset request."""

    filters: ProjectFiltersDict = Field(
        title="Filters",
        description="The filters to apply to project.",
        default_factory=ProjectFiltersDict,
        examples=[{"freenum": "n01", "freenumst": "0"}],
    )
    dest_prj_id: int = Field(
        title="Destination project id",
        description="The destination project ID.",
        examples=[22],
    )
    group_type: GroupDefinitions = Field(
        title="Group type",
        description="Define the groups in which to apply limits. "
        "C for categories, S for samples, A for acquisitions.",
        examples=[GroupDefinitions.acquisitions],
    )
    limit_type: LimitMethods = Field(
        title="Limit type",
        description="The type of limit_value: P for %, V for constant, both per group.",
        examples=[LimitMethods.percent],
    )
    limit_value: float = Field(
        title="Limit value",
        description="Limit value, e.g. 20% or 5 per copepoda or 5% per sample.",
        examples=[10.0],
    )

    model_config = ConfigDict(json_schema_extra={"title": "Subset request Model"})


class SubsetRsp(BaseModel):
    """Subset response."""

    job_id: int = Field(
        title="Job Id",
        description="The job created for this operation.",
        examples=[143],
    )
    # errors: List[str] = Field(title="The errors found during processing",
    #                           default=[])
