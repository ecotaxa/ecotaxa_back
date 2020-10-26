# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import IntEnum
from typing import Optional, Tuple

from DB import User, Role, Project, ProjectPrivilege
from DB.helpers.ORM import Session
from .ProjectPrivilege import ProjectPrivilegeBO


class Action(IntEnum):
    # Global actions
    CREATE_PROJECT = 1
    # Actions on project, by increasing value
    READ = 10
    ANNOTATE = 11  # Write of only certain fields
    ADMINISTRATE = 12  # Read/write/delete


ACTION_TO_PRIV = {Action.ADMINISTRATE: ProjectPrivilegeBO.MANAGE}

NOT_AUTHORIZED = "Not authorized"
NOT_FOUND = "Not found"


class RightsBO(object):
    """
        Centralized place for checking/granting rights over various entities in the app.
    """

    @staticmethod
    def user_wants(session: Session, user_id: int, action: Action, prj_id: int) \
            -> Tuple[User, Project]:
        """
            Check rights for the user to do this specific action onto this project.
        """
        # Load ORM entities
        user: User = session.query(User).get(user_id)
        project = session.query(Project).get(prj_id)
        assert project is not None, NOT_FOUND
        # Check
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            pass
        else:
            a_priv: ProjectPrivilege
            # Collect privileges for user on project
            # noinspection PyTypeChecker
            rights_on_proj = {a_priv.privilege for a_priv in user.privs_on_projects
                              if a_priv.projid == prj_id}
            if action == Action.ADMINISTRATE:
                assert ProjectPrivilegeBO.MANAGE in rights_on_proj, NOT_AUTHORIZED
            elif action == Action.ANNOTATE:
                # TODO: Bah, not nice
                assert ProjectPrivilegeBO.ANNOTATE in rights_on_proj \
                       or ProjectPrivilegeBO.MANAGE in rights_on_proj, NOT_AUTHORIZED
            elif action == Action.READ:
                # TODO: Bah, not nice either
                assert project.visible \
                       or ProjectPrivilegeBO.VIEW in rights_on_proj \
                       or ProjectPrivilegeBO.ANNOTATE in rights_on_proj \
                       or ProjectPrivilegeBO.MANAGE in rights_on_proj, NOT_AUTHORIZED
            else:
                raise Exception("Not implemented")
        return user, project

    @staticmethod
    def user_wants_create_project(session: Session, user_id: int) \
            -> User:
        """
            Check rights for the user to do this specific action, eventually onto this project.
        """
        # Load ORM entities
        user: User = session.query(User).get(user_id)
        assert user is not None, NOT_AUTHORIZED
        # action = Action.CREATE_PROJECT
        # Check
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            pass
        else:
            assert user.has_role(Role.PROJECT_CREATOR), NOT_AUTHORIZED
        return user

    @staticmethod
    def anonymous_wants(session: Session, action: Action, prj_id: int) \
            -> Project:
        """
            Check rights for an anonymous user to do this action.
        """
        # Load ORM entities
        project: Optional[Project] = session.query(Project).get(prj_id)
        # Check
        if project and action == Action.READ:
            assert project.visible, NOT_AUTHORIZED
        else:
            assert False, NOT_AUTHORIZED
        return project

    @staticmethod
    def user_has_role(session: Session, user_id: int, role: str) -> User:
        """
            Check user role. Should be temporary until a proper action is defined, e.g. refresh taxo tree.
        """
        # Load ORM entity
        user: User = session.query(User).get(user_id)
        # Check
        assert user.has_role(role), NOT_AUTHORIZED
        return user

    @staticmethod
    def grant(user: User, action: Action, prj: Project):
        """
            Grant the possibility to do this action on this project to this user.
        """
        privilege = ProjectPrivilege()
        privilege.privilege = ACTION_TO_PRIV[action]
        privilege.project = prj
        user.privs_on_projects.append(privilege)
