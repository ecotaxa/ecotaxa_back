# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Login-related model(s)
#

from helpers.pydantic import BaseModel, ConfigDict, Field


class LoginReq(BaseModel):
    password: str = Field(
        title="User's password", description="User password.", examples=["test!"]
    )
    username: str = Field(
        title="User's email",
        description="User email used during registration.",
        examples=["ecotaxa.api.user@gmail.com"],
    )

    model_config = ConfigDict(json_schema_extra={"title": "Login request Model"})
