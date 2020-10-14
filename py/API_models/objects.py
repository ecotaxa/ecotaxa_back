# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Objects API operations.
#
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from API_models.helpers.DBtoModel import sqlalchemy_to_pydantic
from API_models.helpers.DataclassToModel import dataclass_to_model
from BO.Classification import HistoricalLastClassif, HistoricalClassification
from BO.ObjectSet import ObjectIDListT
from DB import Image, ObjectHeader

ObjectHeaderModel = sqlalchemy_to_pydantic(ObjectHeader)


class ObjectFieldsModel(BaseModel):
    orig_id: str = Field(title="Original object ID from initial TSV load")
    object_link: Optional[str] = Field(title="Object link")


_ImageModelFromDB = sqlalchemy_to_pydantic(Image)


class ImageModel(_ImageModelFromDB):  # type:ignore
    pass


class ObjectModel(ObjectHeaderModel, ObjectFieldsModel):  # type:ignore
    images: List[ImageModel] = Field(title="Images for this object",
                                     default=[])
    free_columns: Dict[str, Any] = Field(title="Free columns from object mapping in project",
                                         default={})


class ObjectSetQueryRsp(BaseModel):
    object_ids: ObjectIDListT = Field(title="Matching object IDs", default=[])
    process_ids: List[Optional[int]] = Field(title="Parent (process) IDs", default=[])
    acquisition_ids: List[Optional[int]] = Field(title="Parent (acquisition) IDs", default=[])
    sample_ids: List[Optional[int]] = Field(title="Parent (sample) IDs", default=[])


HistoricalLastClassificationModel = dataclass_to_model(HistoricalLastClassif)


class ObjectSetRevertToHistoryRsp(BaseModel):
    # TODO: Setting below to List[HistoricalClassification] fails to export the model
    #       but setting as below fools mypy.
    last_entries: List[HistoricalLastClassificationModel] = Field(title="Object + last classification",  # type: ignore
                                                                  default=[])
    # TODO: Below is ClassifSetInfoT but this defeats openapi generator
    classif_info: Dict[int, Any] = Field(title="Classification names (self+parent) for involved IDs",
                                         default={})


class ClassifyReq(BaseModel):
    target_ids: List[int] = Field(title="The IDs of the target objects")
    classifications: List[int] = Field(title="The wanted new classifications, i.e. taxon ID, one for each object. "
                                             " Use -1 to keep present one.")
    wanted_qualification: str = Field(title="The wanted qualifications for all objects. 'V' and 'P'.")


HistoricalClassificationModel = dataclass_to_model(HistoricalClassification)


class ObjectHistoryRsp(BaseModel):
    classif: List[HistoricalClassificationModel] = Field(title="The classification history",  # type:ignore
                                                         default=[])
