# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exported constants, to avoid data duplication b/w back-end and front-end
#
from typing import Dict, List

from BO.DataLicense import DataLicense
from helpers.pydantic import BaseModel, Field


class Constants(BaseModel):
    """ Values which can be considered identical over the lifetime of the back-end """
    license_texts: Dict[str, str] = Field(title="The supported licenses and help text/links",
                                          default={short: expl for short, expl in DataLicense.EXPLANATIONS.items()})
    app_manager: List[str] = Field(title="The application manager identity (name, mail), from config file",
                                         default=["", ""], min_items=2, max_items=2)
