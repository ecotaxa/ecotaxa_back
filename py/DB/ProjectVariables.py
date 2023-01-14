# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from DB.helpers.ORM import Model
from .helpers.DDL import Column, ForeignKey
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR, INTEGER


class ProjectVariables(Model):
    """
        The definition of variables inside a project.
    """
    __tablename__ = 'projects_variables'
    project_id: int = Column(INTEGER, ForeignKey('projects.projid'), primary_key=True)

    # Python expression, the calculation result complies to http://vocab.nerc.ac.uk/collection/P01/current/SSAMPC01/1/
    subsample_coef = Column(VARCHAR)
    # Python expression, the calculation result complies to http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/
    total_water_volume = Column(VARCHAR)
    # Python expression, the calculation result complies to http://vocab.nerc.ac.uk/collection/P01/current/CVOLUKNB/
    individual_biovolume = Column(VARCHAR)

    # The relationship(s) are created in Relations.py but the typing here helps IDE
    project: relationship

    def __str__(self):
        return "{0}:{1}{2}{3}".format(self.project_id, self.subsample_coef, self.total_water_volume,
                                      self.individual_biovolume)
