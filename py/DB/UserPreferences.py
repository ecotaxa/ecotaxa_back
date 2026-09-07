# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy.orm import mapped_column

from .helpers.DDL import ForeignKey, Integer, String
from .helpers.ORM import Model, Mapped


class UserPreferences(Model):
    """
    User preferences per project
    """

    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(
        Integer(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer(), ForeignKey("projects.projid", ondelete="CASCADE"), primary_key=True
    )
    json_prefs: Mapped[str] = mapped_column(String(4096))
