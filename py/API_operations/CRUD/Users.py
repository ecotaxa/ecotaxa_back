# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, List

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
