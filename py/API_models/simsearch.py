# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Optional, Dict

from helpers.pydantic import BaseModel, Field

class SimilaritySearchReq(BaseModel):
    """
    Similarity search request.
    """

    project_id: int = Field(
        title="Project Id",
        description="The destination project, in which we want to find similar objects.",
    )

    target_id: int = Field(
        title="Target Id",
        description="The object we want to find similar objects for.",
    )

    class Config:
        schema_extra = {
            "title": "Similarity Search Request",
            "description": "How to find similar objects, in details.",
            "example": {
                "project_id": 3426,
                "target_id": 1040,
            },
        }


class SimilaritySearchRsp(BaseModel):
    """
    Similarity search response.
    """

    errors: List[str] = Field(
        title="Errors",
        description="Showstopper problems found while preparing the similarity search.",
        example=[],
        default=[],
    )
    warnings: List[str] = Field(
        title="Warnings",
        description="Problems found while preparing the similarity search.",
        example=[],
        default=[],
    )
    job_id: int = Field(
        title="Job Id",
        description="The created job, 0 if there were problems.",
        example=482,
        default=0,
    )
