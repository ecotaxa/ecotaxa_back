# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# The 3 (soon 2) entities under Project and grouping Objects
#
from typing import Optional, List

from API_operations.helpers.Service import Service
from BO.Acquisition import AcquisitionIDListT, EnumeratedAcquisitionSet, AcquisitionBO, AcquisitionIDT, \
    DescribedAcquisitionSet
from BO.ColumnUpdate import ColUpdateList
from BO.Mappings import ProjectMapping
from BO.Process import ProcessIDListT, EnumeratedProcessSet, ProcessIDT, ProcessBO
from BO.Rights import RightsBO, Action
from BO.Sample import SampleIDListT, EnumeratedSampleSet, SampleIDT, SampleBO, DescribedSampleSet, SampleTaxoStats
from BO.User import UserIDT
from DB.Project import ProjectIDT, ProjectIDListT


class SamplesService(Service):
    """
        Basic CRUD operations on Sample.
            The creation is managed during import.
    """

    def query(self, current_user_id: Optional[UserIDT], sample_id: SampleIDT) -> Optional[SampleBO]:
        ret = SampleBO(self.ro_session, sample_id)
        if not ret.exists():
            return None
        assert ret.sample is not None
        assert ret.sample.projid is not None  # TODO: Why need this?
        # Security check
        if current_user_id is None:
            project = RightsBO.anonymous_wants(self.ro_session, Action.READ, ret.sample.projid)
        else:
            _user, project = RightsBO.user_wants(self.session, current_user_id, Action.READ, ret.sample.projid)
        mappings = ProjectMapping().load_from_project(project)
        ret.map_free_columns(mappings.sample_mappings)
        return ret

    def update_set(self, current_user_id: UserIDT, sample_ids: SampleIDListT, updates: ColUpdateList):
        # Get project IDs for the samples and verify rights
        sample_set = EnumeratedSampleSet(self.session, sample_ids)
        prj_ids = sample_set.get_projects_ids()
        # All should be in same project, so far
        assert len(prj_ids) == 1, "Too many or no projects for samples: %s" % sample_ids
        prj_id = prj_ids[0]
        _user, project = RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        assert project  # for mypy
        return sample_set.apply_on_all(project, updates)

    def search(self, current_user_id: Optional[UserIDT],
               project_ids: ProjectIDListT,
               orig_id_pattern: str) -> List[SampleBO]:
        # Security check
        if current_user_id is None:
            [RightsBO.anonymous_wants(self.ro_session, Action.READ, project_id)
             for project_id in project_ids]
        else:
            [RightsBO.user_wants(self.session, current_user_id, Action.READ, project_id)
             for project_id in project_ids]
        sample_set = DescribedSampleSet(self.ro_session, project_ids, orig_id_pattern)
        # mappings = ProjectMapping().load_from_project(project)
        # ret.map_free_columns(mappings.sample_mappings)
        return sample_set.list()

    def read_taxo_stats(self, current_user_id: Optional[UserIDT],
                        sample_ids: SampleIDListT) -> List[SampleTaxoStats]:
        # Get project IDs for the samples and verify rights
        sample_set = EnumeratedSampleSet(self.ro_session, sample_ids)
        project_ids = sample_set.get_projects_ids()
        # Security check
        if current_user_id is None:
            [RightsBO.anonymous_wants(self.ro_session, Action.READ, project_id)
             for project_id in project_ids]
        else:
            [RightsBO.user_wants(self.session, current_user_id, Action.READ, project_id)
             for project_id in project_ids]
        return sample_set.read_taxo_stats()


class AcquisitionsService(Service):
    """
        Basic CRUD operations on Acquisition.
            The creation is managed during import.
    """

    def query(self, current_user_id: Optional[int], acquisition_id: AcquisitionIDT) -> Optional[AcquisitionBO]:
        ret = AcquisitionBO(self.ro_session, acquisition_id)
        if not ret.exists():
            return None
        assert ret.acquis is not None
        # Security check
        if current_user_id is None:
            project = RightsBO.anonymous_wants(self.ro_session, Action.READ, ret.acquis.sample.projid)
        else:
            _user, project = RightsBO.user_wants(self.session, current_user_id, Action.READ, ret.acquis.sample.projid)
        mappings = ProjectMapping().load_from_project(project)
        ret.map_free_columns(mappings.acquisition_mappings)
        return ret

    def update_set(self, current_user_id: int, acquisition_ids: AcquisitionIDListT, updates: ColUpdateList):
        # Get project IDs for the acquisitions and verify rights
        acquisition_set = EnumeratedAcquisitionSet(self.session, acquisition_ids)
        prj_ids = acquisition_set.get_projects_ids()
        # All should be in same project, so far
        assert len(prj_ids) == 1, "Too many or no projects for acquisitions: %s" % acquisition_ids
        prj_id = prj_ids[0]
        _user, project = RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        assert project  # for mypy
        return acquisition_set.apply_on_all(project, updates)

    def search(self, current_user_id: Optional[UserIDT], project_id: ProjectIDT) -> List[AcquisitionBO]:
        # Security check
        if current_user_id is None:
            project = RightsBO.anonymous_wants(self.ro_session, Action.READ, project_id)
        else:
            _user, project = RightsBO.user_wants(self.session, current_user_id, Action.READ, project_id)
        acquisition_set = DescribedAcquisitionSet(self.ro_session, project_id)
        # mappings = ProjectMapping().load_from_project(project)
        # ret.map_free_columns(mappings.sample_mappings)
        return acquisition_set.list()


class ProcessesService(Service):
    """
        Basic CRUD operations on Process.
            The creation is managed during import.
    """

    def query(self, current_user_id: Optional[int], process_id: ProcessIDT) -> Optional[ProcessBO]:
        ret = ProcessBO(self.session, process_id)
        if not ret.exists():
            return None
        assert ret.process is not None
        # Security check
        if current_user_id is None:
            project = RightsBO.anonymous_wants(self.ro_session, Action.READ,
                                               ret.process.acquisition.sample.projid)
        else:
            _user, project = RightsBO.user_wants(self.session, current_user_id, Action.READ,
                                                 ret.process.acquisition.sample.projid)
        mappings = ProjectMapping().load_from_project(project)
        ret.map_free_columns(mappings.process_mappings)
        return ret

    def update_set(self, current_user_id: int, process_ids: ProcessIDListT, updates: ColUpdateList):
        # Get project IDs for the processes and verify rights
        process_set = EnumeratedProcessSet(self.session, process_ids)
        prj_ids = process_set.get_projects_ids()
        # All should be in same project, so far
        assert len(prj_ids) == 1, "Too many or no projects for processes: %s" % process_ids
        prj_id = prj_ids[0]
        _user, project = RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        assert project  # for mypy
        return process_set.apply_on_all(project, updates)
