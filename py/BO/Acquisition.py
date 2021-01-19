# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# An Acquisition business object
#
from typing import List, Any, Dict

from API_models.crud import ColUpdateList
from BO.Classification import ClassifIDT
from BO.Mappings import ProjectMapping
from BO.Project import ProjectIDListT, ProjectIDT
from BO.helpers.MappedEntity import MappedEntity
from BO.helpers.MappedTable import MappedTable
from DB import Session, Query, Project, Acquisition, Sample
from DB.helpers.ORM import any_, ResultProxy
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

AcquisitionIDT = int
AcquisitionIDListT = List[int]  # Typings, to be clear that these are not e.g. project IDs
AcquisitionOrigIDT = str

logger = get_logger(__name__)


class AcquisitionBO(MappedEntity):
    """
        An Acquisition.
    """
    FREE_COLUMNS_ATTRIBUTE = 'acquis'

    def __init__(self, session: Session, acquisition_id: AcquisitionIDT):
        super().__init__(session)
        self.acquis = session.query(Acquisition).get(acquisition_id)

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Sample field somehow then return it """
        return getattr(self.acquis, item)

    @classmethod
    def get_free_fields(cls, acquis: Acquisition, fields_list: List[str]) -> List[Any]:
        """ Get free fields _value_ for the acquisition. """
        mapping = ProjectMapping().load_from_project(acquis.sample.project)
        real_cols = mapping.acquisition_mappings.find_tsv_cols(fields_list)
        if len(real_cols) != len(fields_list):
            raise TypeError("free column not found")
        return [getattr(acquis, real_col) for real_col in real_cols]

    @classmethod
    def get_sums_by_taxon(cls, session: Session, acquis_id: AcquisitionIDT) \
            -> Dict[ClassifIDT, int]:
        res: ResultProxy = session.execute(
            "SELECT o.classif_id, count(1)"
            "  FROM obj_head o "
            " WHERE o.acquisid = :acq"
            " GROUP BY o.classif_id",
            {"acq": acquis_id})
        return {int(classif_id): int(cnt) for (classif_id, cnt) in res.fetchall()}


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
        qry: Query = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Sample)
        qry = qry.join(Acquisition)
        qry = qry.filter(Acquisition.acquisid == any_(self.ids))
        with CodeTimer("Prjs for %d acquisitions: " % len(self.ids), logger):
            return [an_id[0] for an_id in qry.all()]

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
            Apply all updates on all acquisitions.
        """
        return self._apply_on_all(Acquisition, project, updates)

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
        qry: Query = self._session.query(Acquisition)
        qry = qry.join(Sample)
        qry = qry.join(Project)
        qry = qry.filter(Project.projid == self.prj_id)
        ret = [an_acquis for an_acquis in qry.all()]
        return ret
