# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
from typing import Optional, List

from DB import UserPreferences
from DB.User import User, Role
from ..helpers.Service import Service


class UserService(Service):
    """
        Basic CRUD API_operations on User
    """

    def create(self, name, email) -> int:
        usr = User()
        usr.name = name
        usr.email = email
        self.session.add(usr)
        self.session.commit()
        return usr.id

    def search_by_id(self, current_user_id: int, user_id: int) -> Optional[User]:
        ret = self.session.query(User).get(user_id)
        return ret

    def search(self, current_user_id: int, by_name: Optional[str]) -> List[User]:
        qry = self.session.query(User).filter(User.active)
        if by_name is not None:
            qry = qry.filter(User.name.ilike(by_name))
        else:
            return []
        return [a_rec for a_rec in qry]

    def list(self, current_user_id: int) -> List[User]:
        current_user: User = self.session.query(User).get(current_user_id)
        ret = []
        if current_user.has_role(Role.APP_ADMINISTRATOR):
            for usr in self.session.query(User):
                ret.append(usr)
        return ret

    def get_preferences_per_project(self, user_id: int, project_id: int, key: str) -> str:
        """
            Get a preference, for given project and user. Keys are not standardized (for now).
        """
        current_user: User = self.session.query(User).get(user_id)
        prefs_for_proj: UserPreferences = current_user.preferences_for_projects.filter_by(project_id=project_id).first()
        if prefs_for_proj:
            all_prefs_for_proj = json.loads(prefs_for_proj.json_prefs)
        else:
            all_prefs_for_proj = dict()
        return all_prefs_for_proj.get(key, "")

    def set_preferences_per_project(self, user_id: int, project_id: int, key: str, preference: str):
        """
            Set preference for a key, for given project and user. The key disappears if set to empty string.
        """
        current_user: User = self.session.query(User).get(user_id)
        prefs_for_proj: UserPreferences = current_user.preferences_for_projects.filter_by(project_id=project_id).first()
        if prefs_for_proj:
            all_prefs_for_proj = json.loads(prefs_for_proj.json_prefs)
        else:
            prefs_for_proj = UserPreferences()
            prefs_for_proj.project_id = project_id
            prefs_for_proj.user_id = user_id
            self.session.add(prefs_for_proj)
            all_prefs_for_proj = dict()
        all_prefs_for_proj[key] = preference
        if preference == '':
            del all_prefs_for_proj[key]
        prefs_for_proj.json_prefs = json.dumps(all_prefs_for_proj)
        self.session.commit()
