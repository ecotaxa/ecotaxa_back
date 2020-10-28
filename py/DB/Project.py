# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy import Column, Sequence, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER, DOUBLE_PRECISION
from sqlalchemy.orm import relationship

from BO.DataLicense import LicenseEnum
from DB.helpers.ORM import Model

"""
    Possible values for status field.
    TODO: Use an Enum, but it raises problems sending them as SQL values.
"""
ANNOTATE_STATUS = "Annotate"
ANNOTATE_NO_PREDICTION = "Annotate No Prediction"
EXPLORE_ONLY = "ExploreOnly"


class Project(Model):
    """
        Main holder of image data.
    """
    __tablename__ = 'projects'
    projid = Column(INTEGER, Sequence('seq_projects'), primary_key=True)
    title = Column(VARCHAR(255), nullable=False)
    visible = Column(Boolean(), default=True)
    # owner_id = Column(INTEGER, default=0, nullable=False)  # TODO: FK to user
    license = Column(VARCHAR(16), default=LicenseEnum.Copyright, nullable=False)
    status = Column(VARCHAR(40), default=ANNOTATE_STATUS)  # Annotate, ExploreOnly, Annotate No Prediction
    # The mappings for this Project
    # TODO: What happens if there is a conflict from one import to another?
    mappingobj = Column(VARCHAR)
    mappingsample = Column(VARCHAR)
    mappingacq = Column(VARCHAR)
    mappingprocess = Column(VARCHAR)
    # Calculated
    objcount = Column(DOUBLE_PRECISION)
    pctvalidated = Column(DOUBLE_PRECISION)
    pctclassified = Column(DOUBLE_PRECISION)
    # Settings
    classifsettings = Column(VARCHAR)  # Settings for Automatic classification.
    initclassiflist = Column(VARCHAR)  # Initial list of categories
    classiffieldlist = Column(VARCHAR)  # Fields available on sort & displayed field of Manual classif screen
    popoverfieldlist = Column(VARCHAR)  # Fields available on popover of Manual classif screen
    comments = Column(VARCHAR)
    projtype = Column(VARCHAR(50))
    # Note: It's loaded file_s_
    fileloaded = Column(VARCHAR)
    rf_models_used = Column(VARCHAR)
    cnn_network_id = Column(VARCHAR(50))

    # Associated taxonomy statistics. Commented out to avoid that the ORM loads the whole list, which can be big.
    # taxo_stats = relationship("ProjectTaxoStat")

    # The relationships are created in Relations.py but the typing here helps IDE
    all_objects: relationship
    all_samples: relationship
    all_processes: relationship
    all_acquisitions: relationship
    # The users involved somehow in this project
    privs_for_members: relationship
    # owner: relationship
    # The twin EcoPart project
    ecopart_project: relationship

    def __str__(self):
        return "{0} ({1})".format(self.title, self.projid)


class ProjectTaxoStat(Model):
    """
        Taxonomy statistics for a project. One line per taxonomy ID per project.
    """
    __tablename__ = 'projects_taxo_stat'
    projid = Column(INTEGER, ForeignKey('projects.projid', ondelete="CASCADE"), primary_key=True)
    # FK to Taxonomy, but there is the special "-1" value (for unclassified) preventing an official FK
    id = Column(INTEGER, primary_key=True)
    nbr = Column(INTEGER)
    nbr_v = Column(INTEGER)
    nbr_d = Column(INTEGER)
    nbr_p = Column(INTEGER)
