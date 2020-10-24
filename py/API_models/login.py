# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Login-related model(s)
#

from helpers.pydantic import BaseModel, Field


class LoginReq(BaseModel):
    username: str = Field("User email, like in Web UI")
    password: str = Field("User password")
