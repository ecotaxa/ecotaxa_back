# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Taxonomy API operations.
#
from typing import List, Optional

from pydantic import Field
from pydantic.main import BaseModel

from API_models.crud import ProjectSummaryModel
from API_models.helpers.DBtoModel import OrmConfig


class TaxaSearchRsp(BaseModel):
    id: int = Field(title="Id", description="The taxon/category IDs.", example=14334)
    renm_id: Optional[int] = Field(title="Renm_id", description="The advised replacement ID if the taxon/category is deprecated.", example="null")
    text: str = Field(title="Text", description="The taxon name, display one.", example="Bangia")
    pr: int = Field(title="Pr", description="1 if the taxon is in project list, 0 otherwise.", example=0)


# TODO: dataclass_to_model(TaxonBO) to avoid repeated fields
class TaxonModel(BaseModel):
    __config__ = OrmConfig
    id: int = Field(title="Id", description="The taxon/category IDs.", example=1)
    renm_id: Optional[int] = Field(title="Renm id", description="The advised replacement ID if the taxon/category is deprecated.", example="null")
    name: str = Field(title="Name", description="The taxon/category verbatim name.", example="living")
    type: str = Field(title="Type", description="The taxon/category type, 'M' or 'P'.", example="P")
    nb_objects: int = Field(title="Nb objects", description="How many objects are classified in this category.", example=34118)
    nb_children_objects: int = Field(title="Nb children objects", description="How many objects are classified in this category children (not itself).", example=30091727)
    display_name: str = Field(title="Display name", description="The taxon/category display name.", example="living<")
    lineage: List[str] = Field(title="Lineage", description="The taxon/category name of ancestors, including self, in first.", example=["living"])
    id_lineage: List[int] = Field(title="Id lineage", description="The taxon/category IDs of ancestors, including self, in first.", example=[1])
    children: List[int] = Field(title="Children", description="The taxon/category IDs of children.", example=[92952, 2, 92329, 85048, 4, 93599, 93687, 85011, 92951, 93698, 84961, 92696, 3])


class TaxonUsageModel(ProjectSummaryModel):
    nb_validated: int= Field(title="Nb validated", description="How many validated objects in this category in this project.", example=129)

class TaxonomyTreeStatus(BaseModel):
    last_refresh: Optional[str] = Field(title="Last refresh", description="Taxonomy tree last refresh/sync from taxonomy server. "
                                              "Date, with format YYYY-MM-DDThh:mm:ss.", example="2021-10-07T01:26:47")
