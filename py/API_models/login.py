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


class TokenRsp(BaseModel):
    access_token: str = Field(
        title="Access token", description="Bearer token for API calls."
    )
    token_type: str = Field(
        default="bearer", title="Token type", description="Always 'bearer'."
    )
    expires_in: int = Field(
        title="Expires in", description="Access token lifetime, in seconds."
    )
    refresh_token: str = Field(
        title="Refresh token",
        description="Single-use token for /token/refresh, rotated on each use.",
    )
    refresh_expires_in: int = Field(
        title="Refresh expires in", description="Refresh token lifetime, in seconds."
    )

    model_config = ConfigDict(json_schema_extra={"title": "Token response Model"})


class RefreshReq(BaseModel):
    refresh_token: str = Field(
        title="Refresh token",
        description="A refresh token from /token or /token/refresh.",
    )

    model_config = ConfigDict(json_schema_extra={"title": "Refresh request Model"})
