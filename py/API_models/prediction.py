# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Optional, Dict

from helpers.pydantic import BaseModel, Field


class PredictionReq(BaseModel):
    """
        Prediction, AKA Auto Classification, request.
    """
    project_id: int = Field(title="Project Id",
                            description="The destination project, of which objects will be predicted.")
    source_project_ids: List[int] = Field(title="Source project Ids",
                                          description="The source projects, objects in them will serve as reference.",
                                          min_items=1)
    learning_limit: Optional[int] = Field(title="Source projects fetching limit",
                                          description="When set (to a positive value), there will be this number "
                                                      " of objects, _per category_, in the learning set.")
    features: List[str] = Field(title="Features",
                                description="The object features AKA free column, to use in the algorithm. "
                                            "Features must be common to all projects, source ones and destination one.",
                                min_items=1)
    categories: List[int] = Field(title="Categories",
                                  description="In source projects, only objects validated with these categories "
                                              "will be considered.",
                                  min_items=1)
    use_scn: bool = Field(title="Use scn",
                          description="Use extra features, generated using the image, for improving the prediction.",
                          default=False)
    pre_mapping: Dict[int, int] = Field(title="Categories pre-mapping",
                                        description="Categories in keys become value one before "
                                                    "launching the ML algorithm. Any unknown value is ignored.")

    class Config:
        schema_extra = {
            "title": "Prediction Request",
            "description": "How to predict, in details.",
            "example": {
                "project_id": [3426],
                "source_project_ids": [1040, 1820],
                "features": ['area', 'esd'],
                "use_scn": True,
            }
        }


class PredictionRsp(BaseModel):
    """
        Prediction response.
    """
    errors: List[str] = Field(title="Errors",
                              description="Showstopper problems found while preparing the prediction.",
                              example=[], default=[])
    warnings: List[str] = Field(title="Warnings", description="Problems found while preparing the prediction.",
                                example=[], default=[])
    job_id: int = Field(title="Job Id", description="The created job, 0 if there were problems.",
                        example=482, default=0)


class MLModel(BaseModel):
    """
        A ML model for the features, so far just a name.
    """
    name: str = Field(title="Name",
                      description="A usable model for features extraction.",
                      example="zoocam_2022_04_06")
