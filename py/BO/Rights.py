# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import IntEnum
from typing import Optional, Tuple, List

from DB import User, Role, Project, ProjectPrivilege
from DB.helpers.ORM import Session
from .Preferences import Preferences
from .ProjectPrivilege import ProjectPrivilegeBO


class Action(IntEnum):
    # Global actions
    CREATE_PROJECT = 1
    ADMINISTRATE_APP = 2
    ADMINISTRATE_USERS = 3
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
        user = session.query(User).get(user_id)
        assert user is not None
        project = session.query(Project).get(prj_id)
        assert project is not None, NOT_FOUND
        # Check
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            pass
        else:
            a_priv: ProjectPrivilege
            # Collect privileges for user on project
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
        # Keep the last accessed projects
        if Preferences(user).add_recent_project(prj_id):
            session.commit()
        return user, project

    @staticmethod
    def highest_right_on(user: User, prj_id: int) -> str:
        """
            Return the highest right for this user onto this project.
        """
        # Check
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            return ProjectPrivilegeBO.MANAGE
        else:
            a_priv: ProjectPrivilege
            # Collect privileges for user on project
            rights_on_proj = {a_priv.privilege for a_priv in user.privs_on_projects
                              if a_priv.projid == prj_id}
            if ProjectPrivilegeBO.MANAGE in rights_on_proj:
                return ProjectPrivilegeBO.MANAGE
            elif ProjectPrivilegeBO.ANNOTATE in rights_on_proj:
                return ProjectPrivilegeBO.ANNOTATE
            elif ProjectPrivilegeBO.VIEW in rights_on_proj:
                return ProjectPrivilegeBO.VIEW
        return ""

    @staticmethod
    def user_wants_create_project(session: Session, user_id: int) \
            -> User:
        """
            Check rights for the user to do this specific action.
        """
        # Load ORM entity
        user: Optional[User] = session.query(User).get(user_id)
        assert user is not None, NOT_AUTHORIZED
        # Check
        assert Action.CREATE_PROJECT in RightsBO.allowed_actions(user), NOT_AUTHORIZED
        return user

    @staticmethod
    def allowed_actions(user: User) -> List[Action]:
        ret = []
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            ret.extend([Action.CREATE_PROJECT, Action.ADMINISTRATE_APP, Action.ADMINISTRATE_USERS])
        else:
            if user.has_role(Role.PROJECT_CREATOR):
                ret.append(Action.CREATE_PROJECT)
            if user.has_role(Role.USERS_ADMINISTRATOR):
                ret.append(Action.ADMINISTRATE_USERS)
        return ret

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
        user = session.query(User).get(user_id)
        assert user is not None, NOT_FOUND
        # Check
        assert user.has_role(role), NOT_AUTHORIZED
        return user

    @staticmethod
    def grant(session: Session, user: User, action: Action, prj: Project):
        """
            Grant the possibility to do this action on this project to this user.
        """
        privilege = ProjectPrivilege()
        privilege.privilege = ACTION_TO_PRIV[action]
        privilege.project = prj
        privilege.user = user
        session.add(privilege)

