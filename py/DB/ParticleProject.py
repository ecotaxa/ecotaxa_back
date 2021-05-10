# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from .helpers.DDL import Column, ForeignKey, Sequence
from .helpers.ORM import Model
from .helpers.ORM import relationship
from .helpers.Postgres import INTEGER


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
        return "({0})<->({1})".format(self.pprojid, self.projid)


class ParticleSample(Model):
    """
        A sample in particle module, just what's needed to know from EcoTaxa point of view.
    """
    __tablename__ = 'part_samples'
    psampleid = Column(INTEGER, Sequence('part_samples_psampleid_seq'), primary_key=True)
    pprojid = Column(INTEGER, ForeignKey('part_projects.pprojid'))
    sampleid = Column(INTEGER, ForeignKey('samples.sampleid'))

    # The relationships are created in Relations.py but the typing here helps IDE
    ecotaxa_sample: relationship


class ParticleCategoryHistogram(Model):
    __tablename__ = 'part_histocat'
    psampleid = Column(INTEGER, ForeignKey('part_samples.psampleid'), primary_key=True)
    classif_id = Column(INTEGER, primary_key=True)
    lineno = Column(INTEGER, primary_key=True)


class ParticleCategoryHistogramList(Model):
    __tablename__ = 'part_histocat_lst'
    psampleid = Column(INTEGER, ForeignKey('part_samples.psampleid'), primary_key=True)
    classif_id = Column(INTEGER, primary_key=True)


class ParticleCTD(Model):
    __tablename__ = 'part_ctd'
    psampleid = Column(INTEGER, ForeignKey('part_samples.psampleid'), primary_key=True)
