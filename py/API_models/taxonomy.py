# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Taxonomy API operations.
#
from typing import List, Optional, Any, Dict

from fastapi import HTTPException
from pydantic import field_validator, ConfigDict
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from API_models.crud import ProjectSummaryModel
from API_models.helpers.DBtoModel import OrmConfig, combine_models
from BO.TaxoRecast import TaxoRecastBO
from DB.TaxoRecast import RecastOperation
from DB.Taxonomy import Taxonomy
from helpers.pydantic import BaseModel, Field, DescriptiveModel


class TaxoRecastRsp(BaseModel):
    """
    In various contexts, a taxo recast (from taxon -> to taxon) setting.
    """

    from_to: Dict[str, Optional[int]] = Field(
        title="Categories mapping",
        description="Mapping from seen taxon (key) to output replacement one (value)."
        " Use a null replacement to _discard_ the present taxon. Note: keys are strings. Every",
        examples=[{"456": 956, "2456": 213, "9134": None}],
    )
    doc: Optional[Dict[str, str]] = Field(
        title="Mapping documentation",
        description="To keep memory of the reasons for the above mapping. Note: keys are strings.",
        examples=[
            {
                "456": "Up to species",
                "2456": "Up to nearest non-morpho",
                "9134": "Detritus",
            }
        ],
    )

    @field_validator("from_to")
    @classmethod
    def ensure_consistent_renaming(cls, v):
        resp = TaxoRecastBO.valid_remap(v)
        if resp is not None:
            raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, detail=[resp])
        return v

    model_config = ConfigDict(extra="forbid")


class TaxaSearchRsp(BaseModel):
    id: int = Field(title="Id", description="The taxon/category IDs.", examples=[14334])
    status: str = Field(
        title="Status",
        description="The taxon/category status, 'D' for Deprecated, 'A' for Approved or 'N' for Not approved.",
        examples=["P"],
    )
    text: str = Field(
        title="Text", description="The taxon name, display one.", examples=["Bangia"]
    )
    pr: int = Field(
        title="Pr",
        description="1 if the taxon is in project list, 0 otherwise.",
        examples=[0],
    )
    aphia_id: Optional[int] = Field(
        title="Aphia ID",
        description="The WoRMS aphia_id of the taxon.",
        default=None,
        examples=["null"],
    )
    renm_id: Optional[int] = Field(
        title="Renm id",
        description="The advised replacement ID if the taxon/category is deprecated.",
        default=None,
        examples=["null"],
    )
    # TODO: dataclass_to_model(TaxonBO) to avoid repeated fields


# TODO: dataclass_to_model(TaxonBO) to avoid repeated fields
class TaxonModel(BaseModel):
    __config__ = OrmConfig
    id: int = Field(title="Id", description="The taxon/category IDs.", examples=[1])
    name: str = Field(
        title="Name",
        description="The taxon/category verbatim name.",
        examples=["living"],
    )
    type: str = Field(
        title="Type",
        description="The taxon/category type, 'M' for Morpho or 'P' for Phylo.",
        examples=["P"],
    )
    status: str = Field(
        title="Status",
        description="The taxon/category status, 'D' for Deprecated, 'A' for Approved or 'N' for Notapproved.",
        examples=["P"],
    )
    display_name: str = Field(
        title="Display name",
        description="The taxon/category display name.",
        examples=["living<"],
    )
    lineage: List[str] = Field(
        title="Lineage",
        description="The taxon/category name of ancestors, including self, in first.",
        examples=[["living"]],
    )
    id_lineage: List[int] = Field(
        title="Id lineage",
        description="The taxon/category IDs of ancestors, including self, in first.",
        examples=[[1]],
    )
    lineage_status: str = Field(
        title="Id lineage",
        description="The taxon ancestors' status, including self, in first.",
        examples=["DDAAA"],
    )
    renm_id: Optional[int] = Field(
        title="Renm id",
        description="The advised replacement ID if the taxon/category is deprecated.",
        default=None,
        examples=["null"],
    )
    nb_objects: int = Field(
        title="Nb objects",
        description="How many objects are classified in this category.",
        examples=[34118],
    )
    nb_children_objects: int = Field(
        title="Nb children objects",
        description="How many objects are classified in this category children (not itself).",
        examples=[30091727],
    )
    aphia_id: Optional[int] = Field(
        title="Aphia ID",
        description="The WoRMS aphia_id of the taxon.",
        default=None,
        examples=["null"],
    )
    rank: Optional[str] = Field(
        title="Rank",
        description="The WoRMS rank of the taxon.",
        default=None,
        examples=["null"],
    )
    children: List[int] = Field(
        title="Children",
        description="The taxon/category IDs of children.",
        examples=[
            [
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
            ]
        ],
    )


class TaxonUsageModel(ProjectSummaryModel):
    nb_validated: int = Field(
        title="Nb validated",
        description="How many validated objects in this category in this project.",
        examples=[129],
    )


class TaxonomyTreeStatus(BaseModel):
    last_refresh: Optional[str] = Field(
        title="Last refresh",
        description="Taxonomy tree last refresh/sync from taxonomy server. "
        "Date, with format YYYY-MM-DDThh:mm:ss.",
        examples=["2021-10-07T01:26:47"],
    )


class AddWormsTaxonModel(BaseModel):
    aphia_id: Optional[int] = Field(
        title="AphiaId",
        description="The unique numeric aphia_id of the taxon in WoRMS.",
        examples=[12876],
    )


class TaxonomyRecastReq(BaseModel):
    target_id: int = Field(
        title="Target Id", description="The Collection or Project Id.", examples=[3]
    )
    operation: RecastOperation = Field(
        title="Recast operation",
        description="Recast operation name.",
        examples=[RecastOperation.dwca_export_emof],
    )
    is_collection: bool = Field(
        title="Is collection",
        description="If True the target_id is a Collection Id otherwise a Project Id.",
        default=False,
    )
    recast: TaxoRecastRsp = Field(
        title="Recast mapping and doc",
        description="Recast taxonomy from key to value.",
        default=TaxoRecastRsp(from_to={}, doc=None),
        examples=[
            {
                "from_to": {"234": 12, "124": 7},
                "doc": {"234": "up to the nearest non morpho"},
            }
        ],
    )

    @field_validator("recast")
    @classmethod
    def ensure_consistent_renaming(cls, v):
        resp = TaxoRecastBO.valid_remap(v.from_to)
        if resp is not None:
            raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, detail=[resp])
        return v


class _Taxo2Model(DescriptiveModel):
    creation_datetime = Field(
        title="Creation datetime",
        description="Taxon creation date. Date, with format YYYY-MM-DD hh:mm:ss.",
        examples=["2021-08-20 09:09:39"],
    )
    creator_email = Field(
        title="Creator email",
        description="Email of the creator of the taxon.",
        examples=["creator.user@emaim.com"],
    )
    display_name = Field(
        title="Display name",
        description="The display name of the taxon. It is suffixed in EcoTaxoServer with (Deprecated) when taxostatus is 'D'",
        examples=["Echinodermata X"],
    )
    id = Field(
        title="Id", description="The unique numeric id of the taxon.", examples=[12876]
    )
    aphia_id: Optional[int] = Field(
        title="AphiaId",
        description="The unique numeric aphia_id of the taxon if in Worms.",
        examples=[12876],
    )
    rank: Optional[str] = Field(
        title="Rank",
        description="The WoRMS rank of the taxon.",
        examples=["Subphylum"],
    )
    id_instance = Field(
        title="Id instance", description="The instance Id.", examples=[1]
    )
    lastupdate_datetime: Any = Field(
        title="Last update datetime",
        description="Taxon last update. Date, with format YYYY-MM-DD hh:mm:ss.",
        examples=["2021-08-20 09:09:40"],
    )
    name = Field(
        title="Name", description="The name of the taxon.", examples=["Echinodermata X"]
    )
    parent_id = Field(
        title="Parent id",
        description="The unique numeric id of the taxon parent.",
        examples=[11509],
    )
    rename_to = Field(
        title="Rename to",
        description="The advised replacement Name if the taxon is deprecated.",
        examples=["null"],
    )
    source_desc = Field(
        title="Source desc", description="The source description.", examples=["null"]
    )
    source_url = Field(
        title="Source url",
        description="The source url.",
        examples=["https://www.google.fr/"],
    )
    taxostatus = Field(
        title="Taxo status",
        description="The taxon status, N for Not approved, A for Approved or D for Deprecated.",
        examples=["A"],
    )
    taxotype = Field(
        title="Taxo type",
        description="The taxon type, 'M' for Morpho or 'P' for Phylo.",
        examples=["P"],
    )
    nbrobj = Field(
        title="Number of objects",
        description="Number of objects in this category exactly.",
        examples=["5800"],
    )
    nbrobjcum = Field(
        title="Number of descendant objects",
        description="Number of objects in this category and descendant ones.",
        examples=["54800"],
    )

    model_config = ConfigDict(
        json_schema_extra={"title": "Create collection request Model"}
    )


_TaxonCentralModelFromDB = combine_models(Taxonomy, _Taxo2Model)


class TaxonCentral(_TaxonCentralModelFromDB):
    pass
