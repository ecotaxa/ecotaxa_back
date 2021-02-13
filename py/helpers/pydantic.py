# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

# Just to avoid tagging every "pydantic" reference in PyCharm, as pydantic is included in FastAPI
# noinspection PyUnresolvedReferences,PyPackageRequirements
from pydantic import BaseConfig, BaseModel, Field, create_model, root_validator
