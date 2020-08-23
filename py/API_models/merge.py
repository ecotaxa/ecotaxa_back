# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

from helpers.pydantic import BaseModel, Field


# I guess one day we'll have more parameters/options
# class MergeReq(BaseModel):
#     """ Merge request. """
#     src_prj_id: int = Field(title="The source project ID.")


class MergeRsp(BaseModel):
    """ Merge response. """
    errors: List[str] = Field(title="The errors found during processing.",
                              default=[])
