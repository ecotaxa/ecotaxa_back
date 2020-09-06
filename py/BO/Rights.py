# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import IntEnum
from typing import Optional, Tuple

from DB import User, Role, Project, ProjectPrivilege
from DB.Project import ANNOTATE
from DB.ProjectPrivilege import MANAGE
from DB.helpers.ORM import Session


class Action(IntEnum):
    # Global actions
    CREATE_PROJECT = 1
    # Actions on project, by increasing value
    READ = 10
    ANNOTATE = 11  # Write of only certain fields
    ADMINISTRATE = 12  # Read/write/delete


ACTION_TO_PRIV = {Action.ADMINISTRATE: MANAGE}

NOT_AUTHORIZED = "Not authorized"
NOT_FOUND = "Not found"


class RightsBO(object):
    """
        Centralized place for checking/granting rights over various entities in the app.
    """

    @staticmethod
    def user_wants(session: Session, user_id: int, action: Action, prj_id: int = None) -> Tuple[
        User, Optional[Project]]:
        """
            Check rights for the user to do this specific action, eventually onto this project.
        """
        # Load ORM entities
        user: User = session.query(User).get(user_id)
        project: Optional[Project] = None
        if prj_id is not None:
            project = session.query(Project).get(prj_id)
        # Check
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            if action == Action.CREATE_PROJECT:
                pass
            else:
                assert project is not None, NOT_FOUND
        else:
            if action == Action.CREATE_PROJECT:
                assert user.has_role(Role.PROJECT_CREATOR), NOT_AUTHORIZED
            else:
                assert project is not None, NOT_FOUND
                a_priv: ProjectPrivilege
                # Collect privileges for user on project
                rights_on_proj = {a_priv.privilege for a_priv in user.privs_on_projects
                                  if a_priv.projid == prj_id}
                if action == Action.ADMINISTRATE:
                    assert MANAGE in rights_on_proj, NOT_AUTHORIZED
                elif action == Action.ANNOTATE:
                    # TODO: Bah, not nice
                    assert MANAGE in rights_on_proj or ANNOTATE in rights_on_proj, NOT_AUTHORIZED
                elif action == Action.READ:
                    assert project.visible, NOT_AUTHORIZED
                else:
                    raise Exception("Not implemented")
        return user, project

    @staticmethod
    def grant(user: User, action: Action, prj: Project):
        """
            Grant the possibility to do this action on this project to this user.
        """
        privilege = ProjectPrivilege()
        privilege.privilege = ACTION_TO_PRIV[action]
        privilege.project = prj
        user.privs_on_projects.append(privilege)
