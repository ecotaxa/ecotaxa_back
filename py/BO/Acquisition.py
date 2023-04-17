# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# An Acquisition business object
#
from typing import List, Optional, ClassVar

from BO.Classification import ClassifIDListT
from BO.ColumnUpdate import ColUpdateList
from BO.helpers.MappedEntity import MappedEntity
from BO.helpers.MappedTable import MappedTable
from DB import Session
from DB.Acquisition import Acquisition
from DB.Object import ObjectHeader
from DB.Project import ProjectIDT, ProjectIDListT, Project
from DB.Sample import Sample
from DB.helpers.ORM import any_, and_
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

AcquisitionIDT = int
AcquisitionIDListT = List[
    int
]  # Typings, to be clear that these are not e.g. project IDs
AcquisitionOrigIDT = str

logger = get_logger(__name__)


def _get_proj(acq: Acquisition) -> Project:
    return acq.sample.project


class AcquisitionBO(MappedEntity):
    """
    An Acquisition.
    """

    FREE_COLUMNS_ATTRIBUTE: ClassVar = "acquis"
    PROJECT_ACCESSOR: ClassVar = _get_proj
    MAPPING_IN_PROJECT: ClassVar = "acquisition_mappings"

    def __init__(self, session: Session, acquisition_id: AcquisitionIDT):
        super().__init__(session)
        self.acquis = session.query(Acquisition).get(acquisition_id)

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a Sample field somehow then return it"""
        return getattr(self.acquis, item)

    @classmethod
    def get_all_object_ids(
            cls,
            session: Session,
            acquis_id: AcquisitionIDT,
            classif_ids: Optional[ClassifIDListT] = None,
    ) -> List[int]:
        qry = session.query(ObjectHeader.objid)
        qry = qry.join(
            Acquisition,
            and_(
                ObjectHeader.acquisid == Acquisition.acquisid,
                Acquisition.acquisid == acquis_id,
            ),
        )
        if classif_ids is not None:
            qry = qry.filter(ObjectHeader.classif_id.in_(classif_ids))
        return [an_id for an_id, in qry]


class EnumeratedAcquisitionSet(MappedTable):
    """
    A list of acquisitions, known by their IDs.
    """

    def __init__(self, session: Session, ids: AcquisitionIDListT):
        super().__init__(session)
        self.ids = ids

    def get_projects_ids(self) -> ProjectIDListT:
        """
        Return the project IDs for the held sample IDs.
        """
        qry = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Sample)
        qry = qry.join(Acquisition)
        qry = qry.filter(Acquisition.acquisid == any_(self.ids))
        with CodeTimer("Prjs for %d acquisitions: " % len(self.ids), logger):
            return [an_id for an_id, in qry]

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
        Apply all updates on all acquisitions.
        """
        return self._apply_on_all(Acquisition, project, updates.lst)

    def add_filter(self, upd):
        return upd.filter(Acquisition.acquisid == any_(self.ids))


class DescribedAcquisitionSet(object):
    """
    A set of acquisitions, so far all of them for a project.
    """

    def __init__(self, session: Session, prj_id: ProjectIDT):
        self._session = session
        self.prj_id = prj_id

    def list(self) -> List[AcquisitionBO]:
        """
        Return all acquisitions from description.
        TODO: No free columns value so far.
        """
        qry = self._session.query(Acquisition)
        qry = qry.join(Sample)
        qry = qry.join(Project)
        qry = qry.filter(Project.projid == self.prj_id)
        ret = [an_acquis for an_acquis in qry]
        return ret
