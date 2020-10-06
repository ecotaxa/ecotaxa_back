# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

import json
from typing import Any

from BO.Classification import ClassifIDListT
from DB import User, UserPreferences, Session
# Typings, to be clear that these are not e.g. object IDs
from helpers.DynamicLogs import get_logger

UserIDT = int

logger = get_logger(__name__)


class UserBO(object):
    """
        Holder for user-related functions.
    """

    @staticmethod
    def get_preferences_per_project(session: Session, user_id: int, project_id: int, key: str) -> Any:
        """
            Get a preference, for given project and user. Keys are not standardized (for now).
        """
        current_user: User = session.query(User).get(user_id)
        prefs_for_proj: UserPreferences = current_user.preferences_for_projects.filter_by(project_id=project_id).first()
        if prefs_for_proj:
            all_prefs_for_proj = json.loads(prefs_for_proj.json_prefs)
        else:
            all_prefs_for_proj = dict()
        return all_prefs_for_proj.get(key, "")

    @staticmethod
    def set_preferences_per_project(session: Session, user_id: int, project_id: int, key: str, value: Any):
        """
            Set preference for a key, for given project and user. The key disappears if set to empty string.
        """
        current_user: User = session.query(User).get(user_id)
        prefs_for_proj: UserPreferences = current_user.preferences_for_projects.filter_by(project_id=project_id).first()
        if prefs_for_proj:
            all_prefs_for_proj = json.loads(prefs_for_proj.json_prefs)
        else:
            prefs_for_proj = UserPreferences()
            prefs_for_proj.project_id = project_id
            prefs_for_proj.user_id = user_id
            session.add(prefs_for_proj)
            all_prefs_for_proj = dict()
        all_prefs_for_proj[key] = value
        if value == '':
            del all_prefs_for_proj[key]
        prefs_for_proj.json_prefs = json.dumps(all_prefs_for_proj)
        logger.info("for %s and %d: %s", current_user.name, project_id, prefs_for_proj.json_prefs)
        session.commit()

    CLASSIF_MRU_KEY = "mru"
    NB_MRU_KEPT = 10

    @classmethod
    def merge_mru(cls, before: ClassifIDListT, incoming: ClassifIDListT) \
            -> ClassifIDListT:
        """
            Update recently used list.
        """
        bef_tbl = {classif_id: pos_in_mru + 1 for pos_in_mru, classif_id in enumerate(before)}
        inc_tbl = {classif_id: -pos_hist for pos_hist, classif_id in enumerate(incoming)}
        bef_tbl.update(inc_tbl)
        ret = [classif_id for classif_id in sorted(bef_tbl.keys(), key=lambda v: bef_tbl[v])]
        return ret[:cls.NB_MRU_KEPT]

    @classmethod
    def get_mru(cls, session: Session, user_id: int, project_id: int) -> ClassifIDListT:
        """
            Return classification MRU, with a default of empty list.
        """
        ret = cls.get_preferences_per_project(session, user_id, project_id, cls.CLASSIF_MRU_KEY)
        if not ret:
            ret = []
        return ret

    @classmethod
    def set_mru(cls, session: Session, user_id: int, project_id: int, mru:ClassifIDListT):
        """
            Set classification MRU.
        """
        cls.set_preferences_per_project(session, user_id, project_id, cls.CLASSIF_MRU_KEY, mru)
