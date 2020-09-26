# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Objects API operations.
#
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from API_models.helpers.DataclassToModel import dataclass_to_model
from BO.Classification import HistoricalClassif
from BO.ObjectSet import ObjectIDListT


# from BO.ProcessSet import ProcessIDListT


class ObjectSetQueryRsp(BaseModel):
    object_ids: ObjectIDListT = Field(title="Matching object IDs", default=[])
    process_ids: List[Optional[int]] = Field(title="Parent (process) IDs", default=[])
    acquisition_ids: List[Optional[int]] = Field(title="Parent (acquisition) IDs", default=[])
    sample_ids: List[Optional[int]] = Field(title="Parent (sample) IDs", default=[])


HistoricalClassificationModel = dataclass_to_model(HistoricalClassif)


class ObjectSetRevertToHistoryRsp(BaseModel):
    # TODO: Setting below to List[HistoricalClassification] fails to export the model
    #       but setting as below fools mypy.
    last_entries: List[HistoricalClassificationModel] = Field(title="Object + last classification",  # type: ignore
                                                              default=[])
    # TODO: Below is ClassifSetInfoT but this defeats openapi generator
    classif_info: Dict[int, Any] = Field(title="Classification names (self+parent) for involved IDs",
                                          default={})
