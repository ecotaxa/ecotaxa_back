# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from db.Project import Project
from framework.Service import Service


class ProjectService(Service):
    """
        Basic CRUD operations on Project
    """

    def create(self, title: str) -> int:
        prj = Project()
        prj.title = title
        self.session.add(prj)
        self.session.commit()
        return prj.projid
