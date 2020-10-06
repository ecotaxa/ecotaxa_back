# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, List, Any

from BO.Classification import ClassifIDListT
from BO.User import UserBO
from DB.User import User, Role
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service

logger = get_logger(__name__)


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

    def get_preferences_per_project(self, user_id: int, project_id: int, key: str) -> Any:
        """
            Get a preference, for given project and user. Keys are not standardized (for now).
        """
        return UserBO.get_preferences_per_project(self.session, user_id, project_id, key)

    def set_preferences_per_project(self, user_id: int, project_id: int, key: str, value: Any):
        """
            Set preference for a key, for given project and user. The key disappears if set to empty string.
        """
        UserBO.set_preferences_per_project(self.session, user_id, project_id, key, value)

    def update_classif_mru(self, user_id: int, project_id: int, last_used: ClassifIDListT):
        """
            Update recently used list for the user+project.
            :param last_used: The used classif_id, in time order, i.e. recents are in last. No guarantee
                    of uniqueness inside the list.
        """
        mru = UserBO.get_mru(self.session, user_id, project_id)
        mru = UserBO.merge_mru(mru, last_used)
        UserBO.set_mru(self.session, user_id, project_id, mru)
