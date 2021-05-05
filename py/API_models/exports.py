# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

from helpers.pydantic import BaseModel, Field


class EMODnetExportReq(BaseModel):
    """
        EMODNet format export request.
    """
    # meta: EMLMeta = Field(title="EML meta for the produced archive")
    project_ids: List[int] = Field(title="The projects to export", min_items=1)


class EMODnetExportRsp(BaseModel):
    """
        EMODNet format export response.
    """
    errors: List[str] = Field(title="Showstopper problems found while building the archive.",
                              default=[])
    warnings: List[str] = Field(title="Problems found while building the archive, which do not prevent producing it.",
                              default=[])
    job_id: int = Field(title="The created job, 0 if there were problems.",
                         default=0)
