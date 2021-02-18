# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A Sample BO + enumerated set of Sample(s)
#
from typing import List, Any

from API_models.crud import ColUpdateList
from BO.Project import ProjectIDListT
from DB import Session, Query, Project, Sample, Acquisition
from DB.helpers.ORM import any_
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer
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
    PROJECT_ACCESSOR = lambda sam: sam.project
    MAPPING_IN_PROJECT= 'sample_mappings'


    def __init__(self, session: Session, sample_id: SampleIDT):
        super().__init__(session)
        self.sample = session.query(Sample).get(sample_id)

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Sample field somehow then return it """
        return getattr(self.sample, item)

    @classmethod
    def get_acquisitions(cls, session: Session, sample: Sample) -> List[Acquisition]:
        """ Get acquisitions for the sample """
        qry: Query = session.query(Acquisition)
        qry = qry.join(Sample)
        qry = qry.filter(Sample.sampleid == sample.sampleid)
        return qry.all()


class DescribedSampleSet(object):
    """
        A set of samples, so far all of them for a set of projects.
    """

    def __init__(self, session: Session, prj_ids: ProjectIDListT, orig_id_pattern: str):
        self._session = session
        self.prj_ids = prj_ids
        self.pattern = '%' + orig_id_pattern.replace('*', '%') + '%'

    def list(self) -> List[SampleBO]:
        """
            Return all samples from description.
            TODO: No free columns value so far.
        """
        qry: Query = self._session.query(Sample)
        qry = qry.join(Sample, Project.all_samples)
        qry = qry.filter(Project.projid.in_(self.prj_ids))
        qry = qry.filter(Sample.orig_id.ilike(self.pattern))
        ret = [a_sample for a_sample in qry.all()]
        return ret


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
