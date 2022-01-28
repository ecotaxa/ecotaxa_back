# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Global preferences for a user
#
import json
from json import JSONDecodeError

from DB.Project import Project, ProjectIDT
from DB.User import User
from DB.helpers.ORM import Session, Query


class Preferences(object):
    """
        Preferences are stored in column with same name in DB.
    """
    RECENT_PROJECTS_KEY = "proj_mru"
    MAX_MRU_KEPT = 5  # Something tells me it's going to change...

    def __init__(self, user: User):
        self.user = user
        self.prefs = {}
        self.changed = False
        if user.preferences is not None:
            try:
                self.prefs = json.loads(user.preferences)
            except JSONDecodeError:  # pragma:nocover
                self.changed = True

    def add_recent_project(self, prj_id: ProjectIDT) -> bool:
        mru = self.prefs.get(self.RECENT_PROJECTS_KEY)
        if mru is None:
            mru = []
            self.changed = True
            self.prefs[self.RECENT_PROJECTS_KEY] = mru
        if prj_id not in mru:
            mru.append(prj_id)
            if len(mru) > self.MAX_MRU_KEPT:
                mru.pop(0)
            self.changed = True
        if self.changed:
            self.user.preferences = json.dumps(self.prefs)
        return self.changed

    def recent_projects(self, session: Session):
        """
            Return display information for last used projects.
        """
        mru = self.prefs.get(self.RECENT_PROJECTS_KEY, [])
        qry: Query = session.query(Project.projid, Project.title)
        qry = qry.filter(Project.projid.in_(mru))
        qry = qry.order_by(Project.title)
        return [{"projid": projid, "title": title} for projid, title in qry.all()]
