# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import IntEnum
from typing import Optional, Tuple, List, Dict

from DB.Project import Project
from DB.ProjectPrivilege import ProjectPrivilege
from DB.User import User, Role, UserStatus
from DB.helpers.ORM import Session
from BO.DataLicense import AccessLevelEnum
from .Preferences import Preferences
from .ProjectPrivilege import ProjectPrivilegeBO


class Action(IntEnum):
    # Global actions
    CREATE_PROJECT = 1
    ADMINISTRATE_APP = 2
    ADMINISTRATE_USERS = 3
    CREATE_TAXON = 4
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
    def get_user_throw(session: Session, user_id: int) -> User:
        """
        query user by id and active status
        """
        user = session.query(User).get(user_id)
        # not indicating not found -
        assert (
            user is not None and user.status == UserStatus.active.value
        ), NOT_AUTHORIZED
        return user

    @staticmethod
    def get_optional_user(session: Session, user_id: int) -> Optional[User]:
        """
        query optional user by id and active status
        """
        user = session.query(User).get(user_id)
        if user is None or user.status != UserStatus.active.value:
            return None
        else:
            return user

    @staticmethod
    def user_wants(
        session: Session,
        user_id: int,
        action: Action,
        prj_id: int,
        update_preference: Optional[bool] = True,
    ) -> Tuple[User, Project]:
        """
        Check rights for the user to do this specific action onto this project.
        """
        # Load ORM entities
        # user: Optional[User] = session.query(User).get(user_id)
        user: User = RightsBO.get_user_throw(session, user_id)
        # assert user is not None, NOT_AUTHORIZED
        project: Optional[Project] = session.query(Project).get(prj_id)
        assert project is not None, NOT_FOUND
        # Check
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            pass
        else:
            a_priv: ProjectPrivilege
            # Collect privileges for user on project
            rights_on_proj = {
                a_priv.privilege
                for a_priv in user.privs_on_projects
                if a_priv.projid == prj_id
            }

            if action == Action.ADMINISTRATE:
                assert ProjectPrivilegeBO.MANAGE in rights_on_proj, NOT_AUTHORIZED
            elif action == Action.ANNOTATE:
                # TODO: Bah, not nice
                assert (
                    ProjectPrivilegeBO.ANNOTATE in rights_on_proj
                    or ProjectPrivilegeBO.MANAGE in rights_on_proj
                ), NOT_AUTHORIZED
            elif action == Action.READ:
                # TODO: Bah, not nice either
                assert (
                    project.access == AccessLevelEnum.OPEN.value
                    or ProjectPrivilegeBO.VIEW in rights_on_proj
                    or ProjectPrivilegeBO.ANNOTATE in rights_on_proj
                    or ProjectPrivilegeBO.MANAGE in rights_on_proj
                ), NOT_AUTHORIZED
            else:
                raise Exception("Not implemented")
        # Keep the last accessed projects
        if update_preference == True and Preferences(user).add_recent_project(prj_id):
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
            rights_on_proj = {
                a_priv.privilege
                for a_priv in user.privs_on_projects
                if a_priv.projid == prj_id
            }
            if ProjectPrivilegeBO.MANAGE in rights_on_proj:
                return ProjectPrivilegeBO.MANAGE
            elif ProjectPrivilegeBO.ANNOTATE in rights_on_proj:
                return ProjectPrivilegeBO.ANNOTATE
            elif ProjectPrivilegeBO.VIEW in rights_on_proj:
                return ProjectPrivilegeBO.VIEW
        return ""

    @staticmethod
    def user_wants_create_project(session: Session, user_id: int) -> User:
        """
        Check rights for the user to do this specific action.
        """
        # Load ORM entity
        # user: Optional[User] = session.query(User).get(user_id)
        user: User = RightsBO.get_user_throw(session, user_id)
        # assert user is not None, NOT_AUTHORIZED
        # Check
        assert Action.CREATE_PROJECT in RightsBO.get_allowed_actions(
            user
        ), NOT_AUTHORIZED
        return user

    @staticmethod
    def get_allowed_actions(user: User) -> List[Action]:
        ret = []
        if user.has_role(Role.APP_ADMINISTRATOR):
            # King of the world
            ret.extend(
                [
                    Action.CREATE_PROJECT,
                    Action.ADMINISTRATE_APP,
                    Action.ADMINISTRATE_USERS,
                    Action.CREATE_TAXON,
                ]
            )
        else:
            # Any user can create a project
            ret.append(Action.CREATE_PROJECT)
            if user.has_role(Role.USERS_ADMINISTRATOR):
                ret.append(Action.ADMINISTRATE_USERS)
            a_priv: ProjectPrivilege
            for a_priv in user.privs_on_projects:
                if a_priv.privilege == ProjectPrivilegeBO.MANAGE:
                    # If any is managed, OK
                    ret.append(Action.CREATE_TAXON)
                    break
        return ret

    @staticmethod
    def set_allowed_actions(user: User, actions: List[Action], all_roles: Dict):
        """Set roles so that list of actions is possible"""
        roles = set()
        for an_action in actions:
            if an_action == Action.ADMINISTRATE_USERS:
                roles.add(all_roles[Role.USERS_ADMINISTRATOR])
            elif an_action == Action.ADMINISTRATE_APP:
                roles.add(all_roles[Role.APP_ADMINISTRATOR])
        user.roles.clear()
        user.roles.extend(roles)

    @staticmethod
    def anonymous_wants(session: Session, action: Action, prj_id: int) -> Project:
        """
        Check rights for an anonymous user to do this action.
        """
        # Load ORM entities
        project: Optional[Project] = session.query(Project).get(prj_id)
        # Check
        if project and action == Action.READ:
            assert project.access == AccessLevelEnum.OPEN.value, NOT_AUTHORIZED
        else:
            assert False, NOT_AUTHORIZED
        return project

    @staticmethod
    def user_has_role(session: Session, user_id: int, role: str) -> User:
        """
        Check user role. Should be temporary until a proper action is defined, e.g. refresh taxo tree.
        """
        # Load ORM entity
        # user = session.query(User).get(user_id)
        user: User = RightsBO.get_user_throw(session, user_id)
        # assert user is not None, NOT_FOUND
        # Check
        assert user.has_role(role), NOT_AUTHORIZED
        return user

    @staticmethod
    def user_can_add_taxonomy(session: Session, user_id: int) -> User:
        """
        A user can add a taxonomy entry, if he/she is admin on the whole app
        or on any project.
        """
        # Load ORM entity
        # user = session.query(User).get(user_id)
        user: User = RightsBO.get_user_throw(session, user_id)
        # assert user is not None, NOT_FOUND
        # Check
        assert Action.CREATE_TAXON in RightsBO.get_allowed_actions(user), NOT_AUTHORIZED
        return user

    @staticmethod
    def grant(
        session: Session,
        user: User,
        action: Action,
        prj: Project,
        extra: Optional[str] = None,
    ):
        """
        Grant the possibility to do this action on this project to this user.
        """
        privilege = ProjectPrivilege()
        privilege.privilege = ACTION_TO_PRIV[action]
        privilege.projid = prj.projid
        privilege.member = user.id
        privilege.extra = extra
        session.add(privilege)
