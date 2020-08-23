# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in CRUD API_operations.
#
from DB import User, Project
from helpers.pydantic import BaseModel, Field
from .helpers.DBtoModel import sqlalchemy_to_pydantic

UserModel = sqlalchemy_to_pydantic(User)
ProjectModel = sqlalchemy_to_pydantic(Project)


class CreateProjectReq(BaseModel):
    clone_of_id: int = Field(title="If set, clone specified Project",
                             default=None)
    title: str = Field(title="The project title")
    visible: bool = Field(title="The project is created visible",
                          default=True)


class ProjectSearchResult(BaseModel):
    projid: int
    title: str
    status: str
    objcount: int
    pctvalidated: float
    pctclassified: float
    email: str = None
    name: str = None
    visible: bool
