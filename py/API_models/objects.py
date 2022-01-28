# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Objects API operations.
#
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from API_models.helpers.DBtoModel import SQLAlchemy2Pydantic
from API_models.helpers.DataclassToModel import dataclass_to_model
from BO.Classification import HistoricalLastClassif, HistoricalClassification
from BO.ObjectSet import ObjectIDListT
from DB import Image, ObjectHeader
from .helpers.pydantic import ResponseModel


# TODO JCE - examples - ?default?
class _Obj2Model:
    description = {
        "objid": Field(title="Object Id", description="The object Id.", example=264409236),
        "acquisid": Field(title="Acquisition Id", description="The parent acquisition Id.", example=144),
        "orig_id": Field(title="Original id", description="Original object ID from initial TSV load.",
                         example="deex_leg1_48_406"),
        "objdate": Field(title="Object date", description=""),
        "objtime": Field(title="Object time", description=""),
        "latitude": Field(title="Latitude", description="The latitude.", example=42.0231666666667),
        "longitude": Field(title="Longitude", description="The longitude.", example=4.71766666666667),
        "depth_min": Field(title="Depth min", description="The min depth.", example=0),
        "depth_max": Field(title="Depth max", description="The min depth.", example=300),
        "sunpos": Field(title="Sun position", description="Sun position, from date, time and coords.", example="N"),
        "classif_id": Field(title="Classification Id", description="The classification Id.", example=82399),
        "classif_qual": Field(title="Classification qualification",
                              description="The classification qualification. Could be **P** for predicted, **V** for validated or **D** for Dubious.",
                              example="P"),
        "classif_who": Field(title="Classification who", description="The user who manualy classify this object.",
                             example="null"),
        "classif_when": Field(title="Classification when", description="The classification date.",
                              example="2021-09-21T14:59:01.007110"),
        "classif_auto_id": Field(title="Classification auto Id",
                                 description="Set if the object was ever predicted, remain forever with these value. Reflect the 'last state' only if classif_qual is 'P'. "),
        "classif_auto_score": Field(title="Classification auto score",
                                    description="Set if the object was ever predicted, remain forever with these value. Reflect the 'last state' only if classif_qual is 'P'. The classification auto score is generally between 0 and 1. This is a confidence score, in the fact that, the taxon prediction for this object is correct.",
                                    example=0.085),
        "classif_auto_when": Field(title="Classification auto when",
                                   description="Set if the object was ever predicted, remain forever with these value. Reflect the 'last state' only if classif_qual is 'P'. The classification date.",
                                   example="2021-09-21T14:59:01.007110"),
        "classif_crossvalidation_id": Field(title="Classification crossvalidation Id",
                                            description="Always NULL in prod.",
                                            example="null"),
        "complement_info": Field(title="Complement info", description="", example="Part of ostracoda"),
        "similarity": Field(title="Similarity", description="Always NULL in prod.", example="null"),
        "random_value": Field(title="random_value", description=""),
        "object_link": Field(title="Object link", description="Object link.",
                             example="http://www.zooscan.obs-vlfr.fr//")

    }
    exclude: List[str] = []


class ObjectHeaderModel(SQLAlchemy2Pydantic[ObjectHeader, _Obj2Model]):
    pass


class ObjectFieldsModel(BaseModel):
    pass


class _Image2Model:
    description = {
        "imgid": Field(title="Image Id", description="The id of the image.", example=376456),
        "objid": Field(title="Object Id", description="The id of the object related to the image.", example=376456),
        "imgrank": Field(title="Image rank", description="The rank of the image.", example=0),
        "file_name": Field(title="File name", description="The file name.", example="0037/6456.jpg"),
        "orig_file_name": Field(title="Original file name", description="The file name of the original image.",
                                example="dewex_leg2_63_689.jpg"),
        "width": Field(title="Width", description="The width of the image.", example=98),
        "height": Field(title="Height", description="The height of the image.", example=63),
        "thumb_file_name": Field(title="Thumb file name",
                                 description="Generate thumbnail if image is too large. This generated thumbnail file name.",
                                 example="null"),
        "thumb_width": Field(title="Thumb width",
                             description="Generate thumbnail if image is too large. This generated thumbnail width.",
                             example="null"),
        "thumb_height": Field(title="Thumb height",
                              description="Generate thumbnail if image is too large. The thumb height of the image.",
                              example="null")
    }
    exclude: List[str] = []


class _ImageModelFromDB(SQLAlchemy2Pydantic[Image, _Image2Model]):
    pass


class ImageModel(_ImageModelFromDB):
    pass


class ObjectModel(ObjectHeaderModel, ObjectFieldsModel):
    orig_id: str = Field(title="Original id", description="Original object ID from initial TSV load.",
                         example="deex_leg1_48_406")
    object_link: Optional[str] = Field(title="Object link", description="Object link.",
                                       example="http://www.zooscan.obs-vlfr.fr//")
    sample_id: int = Field(title="Sample id", description="Sample (i.e. parent of parent acquisition) ID.", example=12)
    project_id: int = Field(title="Project id", description="Project (i.e. parent of sample) ID.", example=76)
    images: List[ImageModel] = Field(title="Images", description="Images for this object.",
                                     default=[], example=[{
            "imgid": 376456,
            "objid": 376456,
            "imgrank": 0,
            "file_name": "0037/6456.jpg",
            "orig_file_name": "dewex_leg2_63_689.jpg",
            "width": 98,
            "height": 63,
            "thumb_file_name": "null",
            "thumb_width": "null",
            "thumb_height": "null"
        }])
    free_columns: Dict[str, Any] = Field(title="Free columns",
                                         description="Free columns from object mapping in project.",
                                         example={"area": 49.0, "mean": 232.27, "stddev": 2.129}, default={})


class ObjectSetQueryRsp(ResponseModel):
    object_ids: ObjectIDListT = Field(title="Object Ids", description="Matching object IDs.", default=[],
                                      example=[634509, 6234516, 976544])
    acquisition_ids: List[Optional[int]] = Field(title="Acquisition Ids", description="Parent (acquisition) IDs.",
                                                 default=[], example=[23, 987, 89])
    sample_ids: List[Optional[int]] = Field(title="Sample Ids", description="Parent (sample) IDs.", default=[],
                                            example=[234, 194, 12])
    project_ids: List[Optional[int]] = Field(title="Project Ids", description="Project Ids.", default=[],
                                             example=[22, 43])
    details: List[List] = Field(title="Details", description="Requested fields, in request order.",
                                default=[], example=[[7.315666666666667,
                                                      43.685
                                                      ],
                                                     [
                                                         7.315666666666667,
                                                         43.685
                                                     ],
                                                     [
                                                         7.315666666666667,
                                                         43.685
                                                     ]])
    total_ids: int = Field(title="Total Ids", description="Total rows returned by the query, even if it was window-ed.",
                           default=0, example=1000)


class ObjectSetSummaryRsp(ResponseModel):
    """
     Classification summary from object set.
    """
    total_objects: Optional[int] = Field(title="Total objects", description="Total number of objects in the set.",
                                         default=None, example=300)
    validated_objects: Optional[int] = Field(title="Validated objects",
                                             description="Number of validated objects in the set.", default=None,
                                             example=100)
    dubious_objects: Optional[int] = Field(title="Dubious objects", description="Number of dubious objects in the set.",
                                           default=None, example=100)
    predicted_objects: Optional[int] = Field(title="Predicted objects",
                                             description="Number of predicted objects in the set.", default=None,
                                             example=100)


_DBHistoricalLastClassifDescription = {
    "objid": Field(title="Object Id", description="The object Id.", example=264409236),
    "classif_id": Field(title="Classification Id", description="The classification Id.", example=82399),
    "histo_classif_date": Field(title="Historical last classification date", description="The classification date.",
                                example="2021-09-21T14:59:01.007110"),
    "histo_classif_type": Field(title="Historical last classification type",
                                description="The type of classification. Could be **A** for Automatic or **M** for Manual.",
                                example="M"),
    "histo_classif_id": Field(title="Historical last classification Id", description="The classification Id.",
                              example=56),
    "histo_classif_qual": Field(title="Historical last classification qualification",
                                description="The classification qualification. Could be **P** for predicted, **V** for validated or **D** for Dubious.",
                                example="V"),
    "histo_classif_who": Field(title="Historical last classification who",
                               description="The user who manualy classify this object.", example=3876),
}

HistoricalLastClassificationModel = dataclass_to_model(HistoricalLastClassif,  # type:ignore
                                                       field_infos=_DBHistoricalLastClassifDescription)  # type:ignore


class ObjectSetRevertToHistoryRsp(BaseModel):
    # TODO: Setting below to List[HistoricalClassification] fails to export the model
    #       but setting as below fools mypy.
    last_entries: List[HistoricalLastClassificationModel] = Field(title="Last entries", # type: ignore
                                                                  description="Object + last classification",
                                                                  default=[], example=[{"objid": 264409236,
                                                                                        "classif_id": 82399,
                                                                                        "histo_classif_date": "2021-09-21T14:59:01.007110",
                                                                                        "histo_classif_type": "M",
                                                                                        "histo_classif_id": 56,
                                                                                        "histo_classif_qual": "V",
                                                                                        "histo_classif_who": 3876
                                                                                        }])
    # TODO: Below is ClassifSetInfoT but this defeats openapi generator
    classif_info: Dict[int, Any] = Field(title="Classification info",
                                         description="Classification names (self+parent) for involved IDs.",
                                         default={}, example={"25932": ["Oikopleuridae", "Appendicularia"]})


class ClassifyReq(BaseModel):
    target_ids: List[int] = Field(title="Target Ids", description="The IDs of the target objects.",
                                  example=[634509, 6234516, 976544])
    classifications: List[int] = Field(title="Classifications",
                                       description="The wanted new classifications, i.e. taxon ID, one for each object. Use -1 to keep present one.",
                                       example=[7546, 3421, 788])
    wanted_qualification: str = Field(title="Wanted qualification",
                                      description="The wanted qualifications for all objects. 'V' or 'P'.", example="V")


class ClassifyAutoReq(BaseModel):
    target_ids: List[int] = Field(title="Target Ids", description="The IDs of the target objects.")
    classifications: List[int] = Field(title="Classifications",
                                       description="The wanted new classifications, i.e. taxon ID, one for each object.")
    scores: List[float] = Field(title="Scores",
                                description="The classification score is generally between 0 and 1. It indicates the probability that the taxon prediction of this object is correct.")
    keep_log: bool = Field(title="Keep log", description="Set if former automatic classification history is needed.")

    class Config:
        schema_extra = {
            "title": "Classify auto request Model",
            "example": {
                "target_ids": [634509, 6234516, 976544],
                "classifications": [7546, 3421, 788],
                "scores": [0.4, 0.56, 0.38],
                "keep_log": False,
            }
        }


_DBHistoricalClassificationDescription = {
    "objid": Field(title="Object Id", description="The object Id.", example=264409236),
    "classif_id": Field(title="Classification Id", description="The classification Id.", example=82399),
    "classif_date": Field(title="Classification date", description="The classification date.",
                          example="2021-09-21T14:59:01.007110"),
    "classif_who": Field(title="Classification who", description="The user who manualy classify this object.",
                         example="null"),
    "classif_type": Field(title="Classification type",
                          description="The type of classification. Could be **A** for Automatic or **M** for Manual.",
                          example="A"),
    "classif_qual": Field(title="Classification qualification",
                          description="The classification qualification. Could be **P** for predicted, **V** for validated or **D** for Dubious.",
                          example="P"),
    "classif_score": Field(title="Classification score",
                           description="The classification score is generally between 0 and 1. This is a confidence score, in the fact that, the taxon prediction for this object is correct.",
                           example=0.085),
    "user_name": Field(title="User name", description="The name of the user who classified this object.",
                       example="null"),
    "taxon_name": Field(title="Taxon name", description="The taxon name of the object.", example="Penilia avirostris")
}
HistoricalClassificationModel = dataclass_to_model(HistoricalClassification,
                                                   field_infos=_DBHistoricalClassificationDescription)


class ObjectHistoryRsp(ResponseModel):
    classif: List[HistoricalClassificationModel] = Field(title="The classification history",  # type: ignore
                                                         default=[])
