# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, TYPE_CHECKING, Dict, Set

from sqlalchemy import func
from sqlalchemy.orm import Session, mapped_column

from BO.DataLicense import AccessLevelEnum
from DB.helpers.ORM import Model, Mapped

if TYPE_CHECKING:
    from .Sample import Sample
    from .User import User
    from .ProjectVariables import ProjectVariables
    from .Instrument import Instrument
    from .ProjectPrivilege import ProjectPrivilege

from .helpers.DDL import Sequence, ForeignKey
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


class Project(Model):
    """
    Top-level holder of image data.
    """

    __tablename__ = "projects"
    projid: Mapped[int] = mapped_column(
        INTEGER, Sequence("seq_projects"), primary_key=True
    )
    title: Mapped[str] = mapped_column(VARCHAR(255))
    instrument_id: Mapped[str] = mapped_column(
        VARCHAR(32), ForeignKey("instrument.instrument_id")
    )
    access: Mapped[str] = mapped_column(VARCHAR(1), default=AccessLevelEnum.OPEN)
    status: Mapped[str | None] = mapped_column(
        VARCHAR(40), default=ANNOTATE_STATUS
    )  # Annotate, ExploreOnly, Annotate No Prediction
    # The mappings for this Project
    mappingobj: Mapped[str | None] = mapped_column(VARCHAR)
    mappingsample: Mapped[str | None] = mapped_column(VARCHAR)
    mappingacq: Mapped[str | None] = mapped_column(VARCHAR)
    mappingprocess: Mapped[str | None] = mapped_column(VARCHAR)
    # Calculated
    objcount: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    pctvalidated: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    pctclassified: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    # Settings
    classifsettings: Mapped[str | None] = mapped_column(
        VARCHAR
    )  # Settings for Automatic classification.
    initclassiflist: Mapped[str | None] = mapped_column(
        VARCHAR
    )  # Initial list of categories
    classiffieldlist: Mapped[str | None] = mapped_column(
        VARCHAR
    )  # Fields available on sort & displayed field of Manual classif screen
    popoverfieldlist: Mapped[str | None] = mapped_column(
        VARCHAR
    )  # Fields available on popover of Manual classif screen
    comments: Mapped[str | None] = mapped_column(VARCHAR)
    # Note: It's loaded file_s_
    fileloaded: Mapped[str | None] = mapped_column(VARCHAR)
    rf_models_used: Mapped[str | None] = mapped_column(VARCHAR)
    cnn_network_id: Mapped[str | None] = mapped_column(VARCHAR(50))
    # project specific formulae used to calculate concentration and biovolume ( used in project summary export, and collection DarwinCore export)
    formulae: Mapped[str | None] = mapped_column(VARCHAR)
    # Associated taxonomy statistics. Commented out to avoid that the ORM loads the whole list, which can be big.
    # taxo_stats = relationship("ProjectTaxoStat")

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        all_samples: Mapped[List[Sample]]
        # The users involved somehow in this project
        privs_for_members: Mapped[List[ProjectPrivilege]]
        # owner: relationship
        members: Mapped[List[User]]
        # The twin EcoPart project
        # ecopart_project: relationship
        # The related instrument full definition
        instrument: Mapped[Instrument]
        # The variables which can be applied in this project
        variables: Mapped[ProjectVariables]

    def __str__(self):
        return "{0} ({1})".format(self.title, self.projid)

    @classmethod
    def fetch_existing_objects(
        cls, session: Session, prj_id: ProjectIDT
    ) -> Dict[str, int]:
        from .Relations import ObjectHeader, Sample, Acquisition

        qry = session.query(ObjectHeader.orig_id, ObjectHeader.objid)
        qry = qry.join(Acquisition).join(Sample).join(Project)
        qry = qry.filter(Project.projid.__eq__(prj_id))
        qry = qry.filter(ObjectHeader.objid.op("<@")(func.obj_in_prj(prj_id)))
        ret = {orig_id: objid for orig_id, objid in qry}
        return ret

    @classmethod
    def fetch_existing_ranks(
        cls, session: Session, prj_id: ProjectIDT
    ) -> Dict[int, Set[int]]:
        from .Relations import ObjectHeader, Sample, Image, Acquisition

        ret: Dict[int, Set[int]] = {}
        qry = session.query(Image.objid, Image.imgrank)
        qry = qry.join(ObjectHeader).join(Acquisition).join(Sample).join(Project)
        qry = qry.filter(ObjectHeader.objid.op("<@")(func.obj_in_prj(prj_id)))
        qry = qry.filter(Project.projid == prj_id)
        for objid, imgrank in qry:
            ret.setdefault(objid, set()).add(imgrank)
        return ret


class ProjectTaxoStat(Model):
    """
    Taxonomy statistics for a project. One line per taxonomy ID per project.
    """

    __tablename__ = "projects_taxo_stat"
    projid: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE"), primary_key=True
    )
    # FK to Taxonomy, but there is the special "-1" value (for unclassified) preventing an official FK
    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    # Number of objects in this category for this project.
    # NOTE: This can be larger than nbr_v+nbr_d+nbr_p, as objects can be without state but still belong
    # to a category.
    nbr: Mapped[int | None] = mapped_column(INTEGER)
    # Number of validated objects in this category for this project
    nbr_v: Mapped[int | None] = mapped_column(INTEGER)
    # Number of dubious objects in this category for this project
    nbr_d: Mapped[int | None] = mapped_column(INTEGER)
    # Number of predicted objects in this category for this project
    nbr_p: Mapped[int | None] = mapped_column(INTEGER)
