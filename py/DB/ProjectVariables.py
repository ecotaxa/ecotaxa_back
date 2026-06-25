# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, TYPE_CHECKING

from sqlalchemy.orm import mapped_column

from DB.helpers.ORM import Model, Mapped
from .helpers.DDL import ForeignKey
from .helpers.Postgres import VARCHAR, INTEGER

if TYPE_CHECKING:
    from .Project import Project

KNOWN_PROJECT_VARS = {"subsample_coef", "total_water_volume", "individual_volume"}


class ProjectVariables(Model):
    """
    The definition of variables inside a project.
    """

    __tablename__ = "projects_variables"
    project_id: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE"), primary_key=True
    )

    # Python expression, the calculation result complies to http://vocab.nerc.ac.uk/collection/P01/current/SSAMPC01/1/
    subsample_coef: Mapped[str | None] = mapped_column(VARCHAR)
    # Python expression, the calculation result complies to http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/
    total_water_volume: Mapped[str | None] = mapped_column(VARCHAR)
    # Python expression, the implied unit is mm3
    individual_volume: Mapped[str | None] = mapped_column(VARCHAR)

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        project: Mapped[Project]

    def __str__(self):
        return "{0}:{1}{2}{3}".format(
            self.project_id,
            self.subsample_coef,
            self.total_water_volume,
            self.individual_volume,
        )

    def load_from_dict(self, vars_dict: Dict[str, str | None]) -> "ProjectVariables":
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
