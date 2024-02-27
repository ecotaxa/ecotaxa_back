# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A few services for verifying consistency (DB mainly)
#
from typing import List, Any

from BO.ProjectTidying import ProjectTopology
from BO.Rights import RightsBO, Action
from DB import ObjectHeader, Acquisition, Sample, Project, ObjectFields
from helpers.DynamicLogs import LogsSwitcher, LogEmitter
from .helpers.Service import Service


class ProjectConsistencyChecker(Service, LogEmitter):
    """
    With time and bugs, some consistency problems could be introduced in projects.
    This service aims at listing them.
    """

    def __init__(self, prj_id: int):
        super().__init__()
        self.prj_id = prj_id

    def log_file_path(self) -> str:
        return "consistency_%d.log" % self.prj_id

    def run(self, current_user_id: int) -> List[str]:
        with LogsSwitcher(self):
            return self.do_run(current_user_id)

    def do_run(self, current_user_id: int) -> List[str]:
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.READ, self.prj_id)
        # OK
        ret = []
        # TODO: Permissions
        ret.extend(self.check_paths_unicity())
        ret.extend(self.check_acquisid_mirror())
        return ret

    def check_paths_unicity(self) -> List[str]:
        """
        With S for sample, A for acquisition and P for process:
        What happened:
            Import of S1 -> A1 -> P1 -> O1
            Import of S2 -> A1 -> P1 -> O2
        Now there are 2 ways to "go to" P1 from the project
        Since 2.5.0; A and P are merged, but still:
            S1 -> A1+P1 -> O1
            S2 -> A1+P1 -> O2
        """
        ret = []
        topo = ProjectTopology()
        topo.read_from_db(self.session, self.prj_id)
        ret.extend(topo.get_inconsistencies())
        return ret

    def check_partial_time_space(self) -> List[str]:
        """
        Objects which are partially located in time/space.
        """
        return []

    def check_acquisid_mirror(self) -> List[Any]:
        """
        Did we break the assumption that an object's fields are in same acquisition?
        """
        qry = self.ro_session.query(ObjectHeader.objid)
        qry = qry.join(ObjectFields).join(Acquisition).join(Sample).join(Project)

        qry = qry.filter(Project.projid == self.prj_id)
        qry = qry.filter(ObjectHeader.acquisid != ObjectFields.acquis_id)
        broken = [objid for objid, in qry]
        if len(broken) > 0:
            return ["acquisid mirror broken", broken]
        return []
