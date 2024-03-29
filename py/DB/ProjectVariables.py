# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from typing import Dict, Optional

from DB.helpers.ORM import Model
from .helpers.DDL import Column, ForeignKey
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR, INTEGER

KNOWN_PROJECT_VARS = {"subsample_coef", "total_water_volume", "individual_volume"}


class ProjectVariables(Model):
    """
    The definition of variables inside a project.
    """

    __tablename__ = "projects_variables"
    project_id: int = Column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE"), primary_key=True
    )

    # Python expression, the calculation result complies to http://vocab.nerc.ac.uk/collection/P01/current/SSAMPC01/1/
    subsample_coef = Column(VARCHAR)
    # Python expression, the calculation result complies to http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/
    total_water_volume = Column(VARCHAR)
    # Python expression, the implied unit is mm3
    individual_volume = Column(VARCHAR)

    # The relationship(s) are created in Relations.py but the typing here helps IDE
    project: relationship

    def __str__(self):
        return "{0}:{1}{2}{3}".format(
            self.project_id,
            self.subsample_coef,
            self.total_water_volume,
            self.individual_volume,
        )

    def load_from_dict(self, vars_dict: Dict[str, Optional[str]]) -> "ProjectVariables":
        """Load self from a dict with proper keys"""
        for a_var in KNOWN_PROJECT_VARS:
            if a_var in vars_dict:
                a_val = vars_dict[a_var]
                # Map empty string to None i.e. NULL
                a_val = None if a_val is not None and a_val.strip() == "" else a_val
                setattr(self, a_var, a_val)
        return self

    def to_dict(self) -> Dict[str, str]:
        """Dict representation of self"""
        return {a_col: getattr(self, a_col) for a_col in KNOWN_PROJECT_VARS}
