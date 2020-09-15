# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# The 3 (soon 2) entities under Project and grouping Objects
#
from API_models.crud import ColUpdateList
from API_operations.helpers.Service import Service
from BO.AcquisitionSet import AcquisitionIDListT, EnumeratedAcquisitionSet
from BO.ProcessSet import ProcessIDListT, EnumeratedProcessSet
from BO.Rights import RightsBO, Action
from BO.SampleSet import SampleIDListT, EnumeratedSampleSet


class SamplesService(Service):
    """
        Basic CRUD operations on Sample.
            The creation is managed during import.
    """

    def update_set(self, current_user_id: int, sample_ids: SampleIDListT, updates: ColUpdateList):
        # Get project IDs for the samples and verify rights
        sample_set = EnumeratedSampleSet(self.session, sample_ids)
        prj_ids = sample_set.get_projects_ids()
        # All should be in same project, so far
        assert len(prj_ids) == 1, "Too many or no projects for samples: %s" % sample_ids
        prj_id = prj_ids[0]
        _user, project = RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        assert project  # for mypy
        return sample_set.apply_on_all(project, updates)


class AcquisitionsService(Service):
    """
        Basic CRUD operations on Acquisition.
            The creation is managed during import.
    """

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


class ProcessesService(Service):
    """
        Basic CRUD operations on Process.
            The creation is managed during import.
    """

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
