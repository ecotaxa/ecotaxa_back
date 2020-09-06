# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union

from API_models.crud import CreateProjectReq, ProjectSearchResult
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
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
        """
            Create a project, eventually as a clone of another.
        """
        current_user, project = RightsBO.user_wants(self.session, current_user_id, Action.CREATE_PROJECT)
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
        RightsBO.grant(current_user, Action.ADMINISTRATE, prj)
        self.session.commit()
        return prj.projid

    def search(self, current_user_id: int,
               for_managing: bool,
               also_others: bool,
               title_filter: str,
               instrument_filter: str,
               filter_subset: bool) -> List[ProjectSearchResult]:
        # No rights checking as basically everyone can see all projects
        current_user: User = self.session.query(User).get(current_user_id)
        ret = []
        # TODO: Better perf by going thru the iterator instead of a list?
        for prj in ProjectBO.projects_for_user(self.session, current_user, for_managing, also_others,
                                               title_filter, instrument_filter, filter_subset):
            ret.append(prj)
        return ret

    def query(self, current_user_id: int,
              prj_id: int,
              for_managing: bool) -> Project:
        current_user, project = RightsBO.user_wants(self.session, current_user_id,
                                                    Action.ADMINISTRATE if for_managing else Action.READ,
                                                    prj_id)
        # For mypy, should the project be not found there should have been an assert failed before
        assert project is not None

        return project
