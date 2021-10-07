# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Login-related model(s)
#

from helpers.pydantic import BaseModel, Field


class LoginReq(BaseModel):
    password: str = Field(title="User's password", default=None, description="User password", example="test!")
    username: str = Field(title="User's email", default=None, description="User email used during registration",
                          example="ecotaxa.api.user@gmail.com")

    class Config:
        schema_extra = {"title": "Login request Model"}
