# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


from .helpers.DDL import Column, ForeignKey, Integer, String
from .helpers.ORM import Model


class UserPreferences(Model):
    """
    User preferences per project
    """

    __tablename__ = "user_preferences"
    user_id: int = Column(
        Integer(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    project_id: int = Column(
        Integer(), ForeignKey("projects.projid", ondelete="CASCADE"), primary_key=True
    )
    json_prefs: str = Column(String(4096), nullable=False)
