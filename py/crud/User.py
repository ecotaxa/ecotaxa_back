# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from db.User import User
from framework.Service import Service


class UserService(Service):
    """
        Basic CRUD operations on User
    """

    def create(self, name, email) -> int:
        usr = User()
        usr.name = name
        usr.email = email
        self.session.add(usr)
        self.session.commit()
        return usr.id
