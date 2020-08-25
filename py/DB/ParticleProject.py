# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy import Column, ForeignKey, Sequence
from sqlalchemy.dialects.postgresql import INTEGER
from sqlalchemy.orm import relationship

from DB.helpers.ORM import Model


class ParticleProject(Model):
    """
        A project in particle module, just what's needed to know in EcoTaxa.
    """
    __tablename__ = 'part_projects'
    pprojid = Column(INTEGER, Sequence('part_projects_pprojid_seq'), primary_key=True)
    projid = Column(INTEGER, ForeignKey('projects.projid'))

    # The relationships are created in Relations.py but the typing here helps IDE
    ecotaxa_project: relationship

    def __str__(self):
        return "{0} ({1})".format(self.title, self.projid)
