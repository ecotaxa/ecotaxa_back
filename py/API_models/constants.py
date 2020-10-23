# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exported constants, to avoid data duplication b/w back-end and front-end
#
from typing import Dict

from BO.DataLicense import DataLicense
from helpers.pydantic import BaseModel, Field


class Constants(BaseModel):
    license_texts: Dict[str, str] = Field(title="The supported licenses and help text/links",
                                          default={short: expl for short, expl in DataLicense.EXPLANATIONS.items()})
