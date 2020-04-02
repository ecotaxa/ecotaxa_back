# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy import Column, Sequence, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER, DOUBLE_PRECISION
from sqlalchemy.orm import Session

from db.Model import Model


class Project(Model):
    """
        Main holder of image data.
    """
    __tablename__ = 'projects'
    projid = Column(INTEGER, Sequence('seq_projects'), primary_key=True)
    title = Column(VARCHAR(255), nullable=False)
    visible = Column(Boolean(), default=True)
    status = Column(VARCHAR(40), default="Annotate")  # Annotate, ExploreOnly, Annotate No Prediction
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

    def __str__(self):
        return "{0} ({1})".format(self.title, self.projid)

    @staticmethod
    def update_stats(session: Session, projid: int):
        session.execute("""
        UPDATE projects
           SET objcount=q.nbr, pctclassified=100.0*nbrclassified/q.nbr, pctvalidated=100.0*nbrvalidated/q.nbr
          FROM projects p
          LEFT JOIN
             (SELECT projid, sum(nbr) nbr, sum(case when id>0 then nbr end) nbrclassified, sum(nbr_v) nbrvalidated
                FROM projects_taxo_stat
               WHERE projid = :prjid
              GROUP BY projid) q ON p.projid = q.projid
        WHERE projects.projid = :prjid 
          AND p.projid = :prjid""",
                        {'prjid': projid})

    @staticmethod
    def update_taxo_stats(session: Session, projid: int):
        # TODO: There is a direct ref. to obj_head.projid. Problem in case of clean hierarchy.
        session.execute("""
        BEGIN;
        DELETE FROM projects_taxo_stat 
         WHERE projid = :prjid;
        INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p) 
        SELECT projid, coalesce(classif_id, -1) id, count(*) nbr, count(case when classif_qual = 'V' then 1 end) nbr_v,
               count(case when classif_qual = 'D' then 1 end) nbr_d, count(case when classif_qual = 'P' then 1 end) nbr_p
          FROM obj_head
         WHERE projid = :prjid
        GROUP BY projid, classif_id;
        COMMIT;""",
                        {'prjid': projid})


class ProjectTaxoStat(Model):
    """
        Taxonomy statistics for a project. One line per taxonomy ID per project.
    """
    __tablename__ = 'projects_taxo_stat'
    projid = Column(INTEGER, ForeignKey('projects.projid', ondelete="CASCADE"), primary_key=True)
    # FK to Taxonomy
    id = Column(INTEGER, primary_key=True)
    nbr = Column(INTEGER)
    nbr_v = Column(INTEGER)
    nbr_d = Column(INTEGER)
    nbr_p = Column(INTEGER)
