# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Optional

from helpers.pydantic import BaseModel, Field


class SimilaritySearchRsp(BaseModel):
    """
    Similarity search response.
    """

    neighbor_ids: List[int] = Field(
        title="Neighbor IDs",
        description="The list of similar objects IDs.",
    )

    sim_scores: List[float] = Field(
        title="Similarity Scores",
        description="The list of similarity scores, between 0 and 1. The higher the closer, e.g. 1 for the target_id itself.",
    )

    message: Optional[str] = Field(
        title="Message",
        description="A message to the user. If not 'Success' then some condition prevented the computation.",
    )

    class Config:
        schema_extra = {
            "title": "Similarity Search Response",
            "description": "The list of similar objects.",
            "example": {
                "neighbor_ids": [1040, 1041, 1042, 1043, 1044, 1045, 1046, 1047],
                "sim_scores": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3],
                "message": "Success",
            },
        }
