# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from typing import List, TYPE_CHECKING, Iterable

from BO.DataLicense import LicenseEnum, AccessLevelEnum
from DB.helpers.ORM import Model
from .Instrument import Instrument
from .helpers.DDL import Column, Sequence, Boolean, ForeignKey
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR, INTEGER, DOUBLE_PRECISION

"""
    Possible values for status field.
    TODO: Use an Enum, but it raises problems sending them as SQL values.
"""
ANNOTATE_STATUS = "Annotate"
ANNOTATE_NO_PREDICTION = "Annotate No Prediction"
EXPLORE_ONLY = "ExploreOnly"

# Typings, to be clear that these are not e.g. object IDs
ProjectIDT = int
ProjectIDListT = List[int]
if TYPE_CHECKING:
    from .Sample import Sample
    from .ProjectPrivilege import ProjectPrivilege


class Project(Model):
    """
    Top-level holder of image data.
    """

    __tablename__ = "projects"
    projid: int = Column(INTEGER, Sequence("seq_projects"), primary_key=True)
    title: str = Column(VARCHAR(255), nullable=False)
    instrument_id: str = Column(
        VARCHAR(32), ForeignKey(Instrument.instrument_id), nullable=False
    )

    visible = Column(Boolean(), default=True)
    access = Column(VARCHAR(1), default=AccessLevelEnum.OPEN, nullable=False)
    license = Column(VARCHAR(16), default=LicenseEnum.NO_LICENSE, nullable=False)
    status = Column(
        VARCHAR(40), default=ANNOTATE_STATUS
    )  # Annotate, ExploreOnly, Annotate No Prediction
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
    classiffieldlist = Column(
        VARCHAR
    )  # Fields available on sort & displayed field of Manual classif screen
    popoverfieldlist = Column(
        VARCHAR
    )  # Fields available on popover of Manual classif screen
    comments = Column(VARCHAR)
    description = Column(VARCHAR)
    # Note: It's loaded file_s_
    fileloaded = Column(VARCHAR)
    rf_models_used = Column(VARCHAR)
    cnn_network_id = Column(VARCHAR(50))
    # to calculate concentration
    formulae = Column(VARCHAR)
    # Associated taxonomy statistics. Commented out to avoid that the ORM loads the whole list, which can be big.
    # taxo_stats = relationship("ProjectTaxoStat")

    # The relationships are created in Relations.py but the typing here helps IDE
    all_samples: Iterable[Sample]
    # The users involved somehow in this project
    privs_for_members: Iterable[ProjectPrivilege]
    # owner: relationship
    members: relationship
    # The twin EcoPart project
    ecopart_project: relationship
    # The related instrument full definition
    instrument: relationship
    # The variables which can be applied in this project
    variables: relationship

    def __str__(self):
        return "{0} ({1})".format(self.title, self.projid)


class ProjectTaxoStat(Model):
    """
    Taxonomy statistics for a project. One line per taxonomy ID per project.
    """

    __tablename__ = "projects_taxo_stat"
    projid = Column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE"), primary_key=True
    )
    # FK to Taxonomy, but there is the special "-1" value (for unclassified) preventing an official FK
    id = Column(INTEGER, primary_key=True)
    # Number of objects in this category for this project.
    # NOTE: This can be larger than nbr_v+nbr_d+nbr_p, as objects can be without state but still belong
    # to a category.
    nbr = Column(INTEGER)
    # Number of validated objects in this category for this project
    nbr_v = Column(INTEGER)
    # Number of dubious objects in this category for this project
    nbr_d = Column(INTEGER)
    # Number of predicted objects in this category for this project
    nbr_p = Column(INTEGER)
