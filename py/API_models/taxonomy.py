# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Taxonomy API operations.
#
from typing import List, Optional, Any

from API_models.crud import ProjectSummaryModel
from API_models.helpers.DBtoModel import OrmConfig, combine_models
from DB import Taxonomy
from helpers.pydantic import BaseModel, Field


class TaxaSearchRsp(BaseModel):
    id: int = Field(title="Id", description="The taxon/category IDs.", example=14334)
    renm_id: Optional[int] = Field(
        title="Renm_id",
        description="The advised replacement ID if the taxon/category is deprecated.",
        example="null",
    )
    text: str = Field(
        title="Text", description="The taxon name, display one.", example="Bangia"
    )
    pr: int = Field(
        title="Pr",
        description="1 if the taxon is in project list, 0 otherwise.",
        example=0,
    )


# TODO: dataclass_to_model(TaxonBO) to avoid repeated fields
class TaxonModel(BaseModel):
    __config__ = OrmConfig
    id: int = Field(title="Id", description="The taxon/category IDs.", example=1)
    renm_id: Optional[int] = Field(
        title="Renm id",
        description="The advised replacement ID if the taxon/category is deprecated.",
        default=None,
        example="null",
    )
    name: str = Field(
        title="Name", description="The taxon/category verbatim name.", example="living"
    )
    type: str = Field(
        title="Type",
        description="The taxon/category type, 'M' for Morpho or 'P' for Phylo.",
        example="P",
    )
    nb_objects: int = Field(
        title="Nb objects",
        description="How many objects are classified in this category.",
        example=34118,
    )
    nb_children_objects: int = Field(
        title="Nb children objects",
        description="How many objects are classified in this category children (not itself).",
        example=30091727,
    )
    display_name: str = Field(
        title="Display name",
        description="The taxon/category display name.",
        example="living<",
    )
    lineage: List[str] = Field(
        title="Lineage",
        description="The taxon/category name of ancestors, including self, in first.",
        example=["living"],
    )
    id_lineage: List[int] = Field(
        title="Id lineage",
        description="The taxon/category IDs of ancestors, including self, in first.",
        example=[1],
    )
    children: List[int] = Field(
        title="Children",
        description="The taxon/category IDs of children.",
        example=[
            92952,
            2,
            92329,
            85048,
            4,
            93599,
            93687,
            85011,
            92951,
            93698,
            84961,
            92696,
            3,
        ],
    )


class TaxonUsageModel(ProjectSummaryModel):
    nb_validated: int = Field(
        title="Nb validated",
        description="How many validated objects in this category in this project.",
        example=129,
    )


class TaxonomyTreeStatus(BaseModel):
    last_refresh: Optional[str] = Field(
        title="Last refresh",
        description="Taxonomy tree last refresh/sync from taxonomy server. "
        "Date, with format YYYY-MM-DDThh:mm:ss.",
        example="2021-10-07T01:26:47",
    )


class _Taxo2Model(BaseModel):
    creation_datetime: Any = Field(
        title="Creation datetime",
        description="Taxon creation date. Date, with format YYYY-MM-DD hh:mm:ss.",
        example="2021-08-20 09:09:39",
    )
    creator_email: Any = Field(
        title="Creator email",
        description="Email of the creator of the taxon.",
        example="creator.user@emaim.com",
    )
    display_name: Any = Field(
        title="Display name",
        description="The display name of the taxon. It is suffixed in EcoTaxoServer with (Deprecated) when taxostatus is 'D'",
        example="Echinodermata X",
    )
    id: Any = Field(
        title="Id", description="The unique numeric id of the taxon.", example=12876
    )
    id_instance: Any = Field(
        title="Id instance", description="The instance Id.", example=1
    )
    id_source: Any = Field(
        title="Id source", description="The source ID.", example="70372"
    )
    lastupdate_datetime: Any = Field(
        title="Last update datetime",
        description="Taxon last update. Date, with format YYYY-MM-DD hh:mm:ss.",
        example="2021-08-20 09:09:40",
    )
    name: Any = Field(
        title="Name", description="The name of the taxon.", example="Echinodermata X"
    )
    parent_id: Any = Field(
        title="Parent id",
        description="The unique numeric id of the taxon parent.",
        example=11509,
    )
    rename_to: Any = Field(
        title="Rename to",
        description="The advised replacement Name if the taxon is deprecated.",
        example="null",
    )
    source_desc: Any = Field(
        title="Source desc", description="The source description.", example="null"
    )
    source_url: Any = Field(
        title="Source url",
        description="The source url.",
        example="http://www.google.fr/",
    )
    taxostatus: Any = Field(
        title="Taxo status",
        description="The taxon status, N for Not approved, A for Approved or D for Deprecated.",
        example="A",
    )
    taxotype: Any = Field(
        title="Taxo type",
        description="The taxon type, 'M' for Morpho or 'P' for Phylo.",
        example="P",
    )
    nbrobj: Any = Field(
        title="Number of objects",
        description="Number of objects in this category exactly.",
        example="5800",
    )
    nbrobjcum: Any = Field(
        title="Number of descendant objects",
        description="Number of objects in this category and descendant ones.",
        example="54800",
    )


_TaxonCentralModelFromDB = combine_models(Taxonomy, _Taxo2Model)


class TaxonCentral(_TaxonCentralModelFromDB):
    pass
