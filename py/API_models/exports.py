# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

from formats.EMODnet.models import EMLMeta
from helpers.pydantic import BaseModel, Field


class EMODnetExportReq(BaseModel):
    """
        EMODNet format export request.
    """
    meta: EMLMeta = Field(title="EML meta for the produced archive")
    project_ids: List[int] = Field(title="The projects to export", min_items=1)


class EMODnetExportRsp(BaseModel):
    """
        EMODNet format export response.
    """
    task_id: int = Field(title="The created task")
