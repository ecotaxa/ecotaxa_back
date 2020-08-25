# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union

from API_models.crud import CreateProjectReq, ProjectSearchResult
from BO.Project import ProjectBO
from DB.Project import Project, ANNOTATE
from DB.ProjectPrivilege import ProjectPrivilege, MANAGE
from DB.User import User, Role
from DB.helpers.ORM import clone_of
from ..helpers.Service import Service


class ProjectsService(Service):
    """
        Basic CRUD API_operations on Projects
    """

    def create(self, current_user_id: int,
               req: CreateProjectReq) -> Union[int, str]:
        current_user: User = self.session.query(User).filter_by(id=current_user_id).first()
        assert current_user.has_role(Role.APP_ADMINISTRATOR) or current_user.has_role(Role.PROJECT_CREATOR)
        if req.clone_of_id:
            prj = self.session.query(Project).get(req.clone_of_id)
            if prj is None:
                return "Project to clone not found"
            prj = clone_of(prj)
        else:
            prj = Project()
        prj.title = req.title
        prj.status = ANNOTATE
        prj.visible = req.visible
        self.session.add(prj)
        self.session.flush()  # to get the project ID
        # Add the manage privilege
        privilege = ProjectPrivilege()
        privilege.privilege = MANAGE
        privilege.project = prj
        current_user.privs_on_projects.append(privilege)
        self.session.commit()
        return prj.projid

    def search(self, current_user_id: int,
               for_managing: bool,
               also_others: bool,
               title_filter: str,
               instrument_filter: str,
               filter_subset: bool) -> List[ProjectSearchResult]:
        current_user: User = self.session.query(User).get(current_user_id)
        ret = []
        # TODO: Better perf by going thru the iterator instead of a list?
        for prj in ProjectBO.projects_for_user(self.session, current_user, for_managing, also_others,
                                               title_filter, instrument_filter, filter_subset):
            ret.append(prj)
        return ret
