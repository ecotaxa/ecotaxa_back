# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A Sample BO + enumerated set of Sample(s)
#
from typing import List, Dict, Any

from API_models.crud import ColUpdateList
from BO.Project import ProjectIDListT
from DB import Session, Query, Project, Sample, Acquisition, ObjectHeader
from DB.helpers.ORM import any_, ResultProxy, and_
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer
from .Classification import ClassifIDT
from .Mappings import ProjectMapping
from .helpers.MappedEntity import MappedEntity
from .helpers.MappedTable import MappedTable

SampleIDT = int
SampleIDListT = List[int]  # Typings, to be clear that these are not e.g. project IDs
SampleOrigIDT = str

logger = get_logger(__name__)


class SampleBO(MappedEntity):
    """
        A Sample.
    """
    FREE_COLUMNS_ATTRIBUTE = 'sample'

    def __init__(self, session: Session, sample_id: SampleIDT):
        super().__init__(session)
        self.sample = session.query(Sample).get(sample_id)

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Sample field somehow then return it """
        return getattr(self.sample, item)

    @classmethod
    def get_free_fields(cls, sample: Sample, fields_list: List[str]) -> List[Any]:
        """ Get free fields _value_ for the sample. """
        # noinspection PyTypeChecker
        mapping = ProjectMapping().load_from_project(sample.project)
        real_cols = mapping.sample_mappings.find_tsv_cols(fields_list)
        if len(real_cols) != len(fields_list):
            raise TypeError("free column not found")
        return [getattr(sample, real_col) for real_col in real_cols]

    @classmethod
    def get_sums_by_taxon(cls, session: Session, sample_id: SampleIDT) \
            -> Dict[ClassifIDT, int]:
        res: ResultProxy = session.execute(
            "SELECT o.classif_id, count(1)"
            "  FROM obj_head o "
            " WHERE o.sampleid = :smp"
            " GROUP BY o.classif_id",
            {"smp": sample_id})
        return {int(classif_id): int(cnt) for (classif_id, cnt) in res.fetchall()}

    @classmethod
    def get_sums_by_taxon_and_acquisition(cls, session: Session, sample_id: SampleIDT) \
            -> Dict[ClassifIDT, int]:
        res: ResultProxy = session.execute(
            "SELECT o.classif_id, o.acquis_id, count(1)"
            "  FROM obj_head o "
            " WHERE o.sampleid = :smp"
            " GROUP BY o.classif_id, o.acquis_id",
            {"smp": sample_id})
        return {int(classif_id): int(cnt) for (classif_id, cnt) in res.fetchall()}

    @classmethod
    def get_acquisitions(cls, session: Session, sample: Sample) -> List[Acquisition]:
        """ Get acquisitions for the sample """
        qry: Query = session.query(Acquisition)
        # Fill the all_objects relation, we're done with the hierarchy
        qry = qry.join(ObjectHeader, and_(ObjectHeader.projid == sample.projid,
                                          ObjectHeader.sampleid == sample.sampleid,
                                          ObjectHeader.acquisid == Acquisition.acquisid))
        return qry.all()


class EnumeratedSampleSet(MappedTable):
    """
        A list of samples, known by their IDs.
    """

    def __init__(self, session: Session, ids: SampleIDListT):
        super().__init__(session)
        self.ids = ids

    def get_projects_ids(self) -> ProjectIDListT:
        """
            Return the project IDs for the held sample IDs.
        """
        qry: Query = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Sample, Project.all_samples)
        qry = qry.filter(Sample.sampleid == any_(self.ids))
        with CodeTimer("Prjs for %d samples: " % len(self.ids), logger):
            return [an_id[0] for an_id in qry.all()]

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
            Apply all updates on all samples.
        """
        return self._apply_on_all(Sample, project, updates)

    def add_filter(self, upd):
        return upd.filter(Sample.sampleid == any_(self.ids))
