# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in Objects API operations.
#
from typing import List, Optional

from pydantic import BaseModel, Field

from BO.ObjectSet import ObjectIDListT
#from BO.ProcessSet import ProcessIDListT


class ObjectSetQueryRsp(BaseModel):
    object_ids: ObjectIDListT = Field(title="Matching object IDs", default=[])
    process_ids: List[Optional[int]] = Field(title="Parent (process) IDs", default=[])
    acquisition_ids: List[Optional[int]] = Field(title="Parent (acquisition) IDs", default=[])
    sample_ids: List[Optional[int]] = Field(title="Parent (sample) IDs", default=[])
