# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Objects API operations.
#
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from API_models.helpers.DBtoModel import combine_models
from API_models.helpers.DataclassToModel import (
    dataclass_to_model,
    dataclass_to_model_with_suffix,
)
from BO.Classification import HistoricalClassification, HistoricalLastClassif
from BO.ReClassifyLog import ClassifSetInfoT
from DB.Image import Image
from DB.Object import ObjectHeader, ObjectIDListT
from helpers.pydantic import BaseModel, DescriptiveModel, Field


# TODO JCE - examples - ?default?
class _ObjectHeaderModel(DescriptiveModel):
    objid: int = Field(
        title="Object Id", description="The object Id.", examples=[264409236]
    )
    acquisid: int = Field(
        title="Acquisition Id", description="The parent acquisition Id.", examples=[144]
    )
    orig_id: str = Field(
        title="Original id",
        description="Original object ID from initial TSV load.",
        examples=["deex_leg1_48_406"],
    )
    objdate: Optional[date] = Field(title="Object date", description="", default=None)
    objtime: Optional[time] = Field(title="Object time", description="", default=None)
    latitude: Optional[float] = Field(
        title="Latitude",
        description="The latitude.",
        examples=[42.0231666666667],
        default=None,
    )
    longitude: Optional[float] = Field(
        title="Longitude",
        description="The longitude.",
        examples=[4.71766666666667],
        default=None,
    )
    depth_min: Optional[float] = Field(
        title="Depth min", description="The min depth.", examples=[0], default=None
    )
    depth_max: Optional[float] = Field(
        title="Depth max", description="The min depth.", examples=[300], default=None
    )
    sunpos: Optional[str] = Field(
        title="Sun position",
        description="Sun position, from date, time and coords.",
        examples=["N"],
        default=None,
    )
    classif_id: Optional[int] = Field(
        title="Classification Id",
        description="The classification Id.",
        examples=[82399],
        default=None,
    )
    classif_qual: Optional[str] = Field(
        title="Classification qualification",
        description="The classification qualification. Could be **P** for predicted, **V** for validated or **D** for Dubious.",
        examples=["P"],
        default=None,
    )
    classif_who: Optional[int] = Field(
        title="Classification who",
        description="The user who manually classified this object, if **V** or **D**.",
        examples=["null"],
        default=None,
    )
    classif_score: Optional[float] = Field(
        title="Classification who",
        description="The ML score for this object, if **P**.",
        examples=["null"],
        default=None,
    )
    complement_info: Optional[str] = Field(
        title="Complement info",
        description="",
        examples=["Part of ostracoda"],
        default=None,
    )
    # random_value = Field(title="random_value", description="")
    object_link: Optional[str] = Field(
        title="Object link",
        description="Object link.",
        examples=["http://www.zooscan.obs-vlfr.fr//"],
        default=None,
    )


_ObjectHeaderModelFromDB = combine_models(ObjectHeader, _ObjectHeaderModel)


class _ObjectHeaderComplement(BaseModel):
    # Still there but now computed
    classif_when: Optional[datetime] = Field(
        title="Classification when",
        description="The human classification date, if **P** or **V**.",
        examples=["2021-09-21T14:59:01.007110"],
        default=None,
    )
    classif_auto_id: Optional[int] = Field(
        title="Classification auto Id",
        description="Set if the object was ever predicted, remains forever with these value. Reflect the 'last state' only if classif_qual is 'P'. ",
        default=None,
    )  # Used to be directly available, now needs more calculations.
    classif_auto_score: Optional[float] = Field(
        title="Classification auto score",
        description="Set if the object was ever predicted, remains forever with these value. Reflect the 'last state' only if classif_qual is 'P'. The classification auto score is generally between 0 and 1. This is a confidence score, in the fact that, the taxon prediction for this object is correct.",
        examples=[0.085],
        default=None,
    )
    classif_auto_when: Optional[datetime] = Field(
        title="Classification auto when",
        description="Set if the object was ever predicted, remains forever with these value. Reflect the 'last state' only if classif_qual is 'P'. The classification date.",
        examples=["2021-09-21T14:59:01.007110"],
        default=None,
    )
    complement_info: str = Field(
        title="Complement info", description="", examples=["Part of ostracoda"]
    )
    object_link: Optional[str] = Field(
        title="Object link",
        description="Object link.",
        examples=["http://www.zooscan.obs-vlfr.fr//"],
        default=None,
    )


class ObjectHeaderModel(_ObjectHeaderModelFromDB, _ObjectHeaderComplement):
    pass


class _Image2Model(DescriptiveModel):
    imgid = Field(
        title="Image Id", description="The id of the image.", examples=[376456]
    )
    objid = Field(
        title="Object Id",
        description="The id of the object related to the image.",
        examples=[376456],
    )
    imgrank = Field(
        title="Image rank", description="The rank of the image.", examples=[0]
    )
    orig_file_name = Field(
        title="Original file name",
        description="The file name of the original image.",
        examples=["dewex_leg2_63_689.jpg"],
    )
    width = Field(title="Width", description="The width of the image.", examples=[98])
    height = Field(
        title="Height", description="The height of the image.", examples=[63]
    )
    thumb_width = Field(
        title="Thumb width",
        description="Generate thumbnail if image is too large. This generated thumbnail width.",
        examples=["null"],
    )
    thumb_height = Field(
        title="Thumb height",
        description="Generate thumbnail if image is too large. The thumb height of the image.",
        examples=["null"],
    )


_ImageModelFromDB = combine_models(Image, _Image2Model)


class ImageModel(_ImageModelFromDB):
    """Computed inside ObjectBO"""

    file_name: str = Field(
        title="File name", description="The file name.", examples=["0037/6456.jpg"]
    )
    thumb_file_name: Optional[str] = Field(
        title="Thumb file name",
        description="If image was too large at import time, the generated thumbnail file name.",
        examples=["null"],
        default=None,
    )


class ObjectModel(ObjectHeaderModel, _ObjectHeaderComplement):
    orig_id: str = Field(
        title="Original id",
        description="Original object ID from initial TSV load.",
        examples=["deex_leg1_48_406"],
    )
    object_link: Optional[str] = Field(
        title="Object link",
        description="Object link.",
        examples=["http://www.zooscan.obs-vlfr.fr//"],
        default=None,
    )
    sample_id: int = Field(
        title="Sample id",
        description="Sample (i.e. parent of parent acquisition) ID.",
        examples=[12],
    )
    project_id: int = Field(
        title="Project id",
        description="Project (i.e. parent of sample) ID.",
        examples=[76],
    )
    images: List[ImageModel] = Field(
        title="Images",
        description="Images for this object.",
        default=[],
        examples=[
            [
                {
                    "imgid": 376456,
                    "objid": 376456,
                    "imgrank": 0,
                    "file_name": "0037/6456.jpg",
                    "orig_file_name": "dewex_leg2_63_689.jpg",
                    "width": 98,
                    "height": 63,
                    "thumb_file_name": "null",
                    "thumb_width": "null",
                    "thumb_height": "null",
                }
            ]
        ],
    )
    free_columns: Dict[str, Any] = Field(
        title="Free columns",
        description="Free columns from object mapping in project.",
        examples=[{"area": 49.0, "mean": 232.27, "stddev": 2.129}],
        default={},
    )
    classif_crossvalidation_id: Optional[int] = Field(
        title="Classification crossvalidation Id",
        description="Always NULL, kept for compat.",
        examples=["null"],
        default=None,
    )
    similarity: Optional[float] = Field(
        title="Similarity",
        description="Always NULL, kept for compat.",
        examples=["null"],
        default=None,
    )
    random_value: int = Field(
        title="random_value",
        description="Random value associated to an image",
        examples=[1234],
    )


class ObjectSetQueryRsp(BaseModel):
    object_ids: ObjectIDListT = Field(
        title="Object Ids",
        description="Matching object IDs.",
        default=[],
        examples=[[634509, 6234516, 976544]],
    )
    acquisition_ids: List[Optional[int]] = Field(
        title="Acquisition Ids",
        description="Parent (acquisition) IDs.",
        default=[],
        examples=[[23, 987, 89]],
    )
    sample_ids: List[Optional[int]] = Field(
        title="Sample Ids",
        description="Parent (sample) IDs.",
        default=[],
        examples=[[234, 194, 12]],
    )
    project_ids: List[Optional[int]] = Field(
        title="Project Ids", description="Project Ids.", default=[], examples=[[22, 43]]
    )
    details: List[List[Any]] = Field(
        title="Details",
        description="Requested fields, in request order.",
        default=[],
        examples=[
            [
                [7.315666666666667, 43.685],
                [7.315666666666667, 43.685],
                [7.315666666666667, 43.685],
            ]
        ],
    )
    total_ids: int = Field(
        title="Total Ids",
        description="Total rows returned by the query, even if it was window-ed.",
        default=0,
        examples=[1000],
    )


class ObjectSetSummaryRsp(BaseModel):
    """
    Classification summary from object set.
    """

    total_objects: Optional[int] = Field(
        title="Total objects",
        description="Total number of objects in the set.",
        default=None,
        examples=[300],
    )
    validated_objects: Optional[int] = Field(
        title="Validated objects",
        description="Number of validated objects in the set.",
        default=None,
        examples=[100],
    )
    dubious_objects: Optional[int] = Field(
        title="Dubious objects",
        description="Number of dubious objects in the set.",
        default=None,
        examples=[100],
    )
    predicted_objects: Optional[int] = Field(
        title="Predicted objects",
        description="Number of predicted objects in the set.",
        default=None,
        examples=[100],
    )


class _DBHistoricalLastClassifDescription(DescriptiveModel):
    objid = Field(title="Object Id", description="The object Id.", examples=[264409236])
    classif_id = Field(
        title="Classification Id",
        description="The classification Id.",
        examples=[82399],
    )
    histo_classif_date = Field(
        title="Historical last classification date",
        description="The classification date.",
        examples=["2021-09-21T14:59:01.007110"],
    )
    histo_classif_type = Field(
        title="Historical last classification type",
        description="The type of classification. Could be **A** for Automatic or **M** for Manual.",
        examples=["M"],
        # TODO: Is one of 'A', 'M', or 'n' for no history
    )
    histo_classif_id = Field(
        title="Historical last classification Id",
        description="The classification Id.",
        examples=[56],
    )
    histo_classif_qual = Field(
        title="Historical last classification qualification",
        description="The classification qualification. Could be **P** for predicted, **V** for validated or **D** for Dubious.",
        examples=["V"],
    )
    histo_classif_who = Field(
        title="Historical last classification who",
        description="The user who manually classified this object.",
        examples=[3876],
    )
    histo_classif_score = Field(
        title="Historical last classification score",
        description="The score for auto classification.",
        examples=[0.52],
    )


HistoricalLastClassificationModel = dataclass_to_model_with_suffix(
    HistoricalLastClassif, _DBHistoricalLastClassifDescription
)


class ObjectSetRevertToHistoryRsp(BaseModel):
    last_entries: List[HistoricalLastClassificationModel] = Field(
        title="Last entries",
        description="Object + last classification",
        default=[],
        examples=[
            [
                {
                    "objid": 264409236,
                    "classif_id": 82399,
                    "histo_classif_date": "2021-09-21T14:59:01.007110",
                    "histo_classif_type": "M",
                    "histo_classif_id": 56,
                    "histo_classif_qual": "V",
                    "histo_classif_who": 3876,
                }
            ]
        ],
    )

    classif_info: ClassifSetInfoT = Field(
        title="Classification info",
        description="Classification names (self+parent) for involved IDs.",
        default={},
        examples=[{"25932": ["Oikopleuridae", "Appendicularia"]}],
    )


class ClassifyReq(BaseModel):
    target_ids: List[int] = Field(
        title="Target Ids",
        description="The IDs of the target objects.",
        examples=[[634509, 6234516, 976544]],
    )
    classifications: List[int] = Field(
        title="Classifications",
        description="The wanted new classifications, i.e. taxon ID, one for each object. Use -1 to keep present one.",
        examples=[[7546, 3421, 788]],
    )
    wanted_qualification: str = Field(
        title="Wanted qualification",
        description="The wanted qualifications for all objects. 'V' or 'P'.",
        examples=["V"],
    )


class ClassifyAutoReq(BaseModel):
    target_ids: List[int] = Field(
        title="Target Ids", description="The IDs of the target objects."
    )
    classifications: List[int] = Field(
        title="Classifications",
        description="The wanted new classifications, i.e. taxon ID, one for each object.",
    )
    scores: List[float] = Field(
        title="Scores",
        description="The classification score is generally between 0 and 1. It indicates the probability that the taxon prediction of this object is correct.",
    )
    keep_log: bool = Field(
        title="Keep log",
        description="Set if former automatic classification history is needed.",
    )


class ClassifyAutoReqMult(BaseModel):
    target_ids: List[int] = Field(
        title="Target Ids", description="The IDs of the target objects."
    )
    classifications: List[List[int]] = Field(
        title="Classifications",
        description="The wanted new classifications, i.e. taxon ID, one list for each object.",
    )
    scores: List[List[float]] = Field(
        title="Scores",
        description="The classification scores, between 0 and 1. Each indicates the probability that the taxon prediction of this object for this category is correct.",
    )
    keep_log: bool = Field(
        title="Keep log",
        description="Set if former automatic classification history is needed. Deprecated, always True.",
    )

    class Config:
        json_schema_extra = {
            "title": "Classify auto request Model",
            "example": {
                "target_ids": [634509, 6234516, 976544],
                "classifications": [[7546], [3421, 5614], [788]],
                "scores": [[0.4], [0.56, 0.3333], [0.38]],
                "keep_log": False,
            },
        }


class _DBHistoricalClassificationDescription(DescriptiveModel):
    objid = Field(title="Object Id", description="The object Id.", examples=[264409236])
    classif_id = Field(
        title="Classification Id",
        description="The classification Id.",
        examples=[82399],
    )
    classif_date = Field(
        title="Classification date",
        description="The classification date.",
        examples=["2021-09-21T14:59:01.007110"],
    )
    classif_who = Field(
        title="Classification who",
        description="The user who manually classified this object.",
        examples=["null"],
    )
    classif_type = Field(
        title="Classification type",
        description="The type of classification. Could be **A** for Automatic or **M** for Manual.",
        examples=["A"],
    )
    classif_qual = Field(
        title="Classification qualification",
        description="The classification qualification. Could be **P** for predicted, **V** for validated or **D** for Dubious.",
        examples=["P"],
    )
    classif_score = Field(
        title="Classification score",
        description="The classification score is generally between 0 and 1. This is a confidence score, in the fact that, the taxon prediction for this object is correct.",
        examples=[0.085],
    )
    user_name = Field(
        title="User name",
        description="The name of the user who classified this object.",
        examples=["null"],
    )
    taxon_name = Field(
        title="Taxon name",
        description="The taxon name of the object.",
        examples=["Penilia avirostris"],
    )


HistoricalClassificationModel = dataclass_to_model(
    HistoricalClassification, _DBHistoricalClassificationDescription
)


class ObjectHistoryRsp(BaseModel):
    classif: List[HistoricalClassificationModel] = Field(
        title="The classification history", default=[]
    )
