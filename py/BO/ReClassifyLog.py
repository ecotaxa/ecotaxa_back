# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Remember the mass move of objects from one category to another, inside a project.
#
from typing import List, Dict, Tuple

from BO.Classification import ClassifIDT, ClassifIDListT
from DB import Taxonomy
from DB.Project import ProjectIDT
from DB.Taxonomy import TaxonomyChangeLog
from DB.helpers.ORM import Session, any_, func
from helpers.DynamicLogs import get_logger

ClassifSetInfoT = Dict[ClassifIDT, Tuple[str, str]]

logger = get_logger(__name__)


class ReClassificationBO(object):
    """
        The DB table @see TaxonomyChangeLog keeps atomic changes, but for querying we
        need mostly aggregates.
    """

    @staticmethod
    def add_log(session: Session, from_id: ClassifIDT, to_id: ClassifIDT,
                project_id: ProjectIDT, why: str, impacted: int):
        """
            Add a log line.
        """
        new_line = TaxonomyChangeLog()
        new_line.from_id = from_id
        new_line.to_id = to_id
        new_line.project_id = project_id
        new_line.why = why
        new_line.impacted = impacted
        new_line.occurred_on = func.now()
        session.add(new_line)
        session.commit()

    @staticmethod
    def previous_choices(session: Session, src_ids: ClassifIDListT) -> Dict[ClassifIDT, ClassifIDT]:
        """
            Return the non-advised choice made in the majority of projects, in the past, for these categories.
        """
        qry = session.query(TaxonomyChangeLog.from_id, TaxonomyChangeLog.to_id,
                            func.count(TaxonomyChangeLog.project_id))
        qry = qry.join(Taxonomy, Taxonomy.id == TaxonomyChangeLog.from_id)
        qry = qry.filter(TaxonomyChangeLog.from_id == any_(src_ids))
        qry = qry.filter(TaxonomyChangeLog.to_id != Taxonomy.rename_to)  # Exclude advised
        qry = qry.group_by(TaxonomyChangeLog.from_id, TaxonomyChangeLog.to_id)
        # Present the most projects first, and if deuce take the most recent first
        qry = qry.order_by(func.count(TaxonomyChangeLog.project_id).desc(),
                           func.max(TaxonomyChangeLog.occurred_on))
        ret = {}
        for from_id, to_id, nb_prjs in qry.all():
            if from_id not in ret:
                # Pick the best match, i.e. first in result
                ret[from_id] = to_id
        return ret

    @staticmethod
    def history_for_project(session: Session, project_id: ProjectIDT) -> List[Dict]:
        """
            Return the choices made on this project during classification.
        """
        qry = session.query(TaxonomyChangeLog.from_id, TaxonomyChangeLog.to_id, Taxonomy.name)
        qry = qry.join(Taxonomy, Taxonomy.id == TaxonomyChangeLog.to_id)
        qry = qry.filter(TaxonomyChangeLog.project_id == project_id)
        qry = qry.order_by(TaxonomyChangeLog.occurred_on)
        return [{"from": from_id, "to": to_id, "name": to_name}
                for from_id, to_id, to_name in qry.all()]
