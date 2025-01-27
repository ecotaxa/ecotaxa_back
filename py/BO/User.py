# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

import json
from dataclasses import dataclass
from typing import Any, Final, List, Optional

from BO.Classification import ClassifIDListT
from BO.Rights import RightsBO
from BO.helpers.TSVHelpers import none_to_empty
from DB import Session
from DB.User import User, UserStatus, UserType, Person, Guest
from DB.Organization import Organization
from DB.UserPreferences import UserPreferences
from DB.helpers.ORM import any_, or_, func
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

# Typings, to be clear that these are not e.g. object IDs
UserIDT = int
UserIDListT = List[int]

logger = get_logger(__name__)

MISSING_USER = {"id": -1, "name": "", "email": ""}

USER_PWD_REGEXP = r"^(?:(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#?%^&*-+])).{8,20}$"
USER_PWD_REGEXP_DESCRIPTION = "8 char. minimum, at least one uppercase, one lowercase, one number and one special char in '#?!@%^&*-+' "
SHORT_TOKEN_AGE = 1
PROFILE_TOKEN_AGE = 24


class OrganizationBO(object):
    @staticmethod
    def find_organizations(
        session: Session, names: List[str], found_organizations: dict
    ):
        """
        Find the organizations in DB, by name.
        :param session:
        :param names:
        :param found_organizations: A dict in
        """
        qry = session.query(Organization.name, Organization.directories).filter(
            func.lower(Organization.name) == any_(names)
        )
        res = qry.all()
        for rec in res:
            for u in found_organizations:
                if u == rec[0]:
                    found_organizations[u]["name"] = rec[0]


class PersonBO(object):
    """
    Holder for user-related functions.
    """

    def __init__(self, person: Person):
        self._person = person

    @staticmethod
    def find_persons(
        session: Session, names: List[str], emails: List[str], found_persons: dict
    ):
        """
        Find the persons in DB, by name or email.
        :param session:
        :param emails:
        :param names:
        :param found_persons: A dict in
        """
        qry = session.query(Person.id, Person.name, Person.email).filter(
            or_(
                func.lower(Person.name) == any_(names),
                func.lower(Person.email) == any_(emails),
            )
        )
        res = qry.all()
        print("___res___", res)
        for rec in res:
            for u in found_persons:
                if (
                    u == rec[1]
                    or none_to_empty(found_persons[u].get("email")).lower() == rec[2]
                ):
                    found_persons[u]["id"] = rec[0]
        print("___found_persons", found_persons)


class GuestBO(object):
    """
    Holder for user-related functions.
    """

    def __init__(self, guest: Guest):
        self._guest = guest

    @staticmethod
    def find_guests(
        session: Session, names: List[str], emails: List[str], found_guests: dict
    ):
        """
        Find the persons in DB, by name or email.
        :param session:
        :param emails:
        :param names:
        :param found_guests: A dict in
        """
        qry = session.query(Guest.id, Guest.name, Guest.email).filter(
            or_(
                func.lower(Guest.name) == any_(names),
                func.lower(Guest.email) == any_(emails),
            )
        )
        res = qry.all()
        print("___res___", res)
        for rec in res:
            for u in found_guests:
                if (
                    u == rec[1]
                    or none_to_empty(found_guests[u].get("email")).lower() == rec[2]
                ):
                    found_guests[u]["id"] = rec[0]
        print("___found_guests", found_guests)


class UserBO(object):
    """
    Holder for user-related functions.
    """

    def __init__(self, user: User):
        self._user = user

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a Project field somehow then return it"""
        return getattr(self._user, item)

    @staticmethod
    def find_users(
        session: Session, names: List[str], emails: List[str], found_users: dict
    ):
        """
        Find the users in DB, by name or email.
        :param session:
        :param emails:
        :param names:
        :param found_users: A dict in
        """
        qry = (
            session.query(User.id, func.lower(User.name), func.lower(User.email))
            .filter(
                or_(
                    func.lower(User.name) == any_(names),
                    func.lower(User.email) == any_(emails),
                )
            )
            .filter(User.type == UserType.user.value)
        )
        res = qry.all()
        for rec in res:
            for u in found_users:
                if (
                    u == rec[1]
                    or none_to_empty(found_users[u].get("email")).lower() == rec[2]
                ):
                    found_users[u]["id"] = rec[0]
        print("___found_users", found_users)

    @staticmethod
    def get_preferences_per_project(
        ro_session: Session, user_id: int, project_id: int, key: str
    ) -> Any:
        """
        Get a preference, for given project and user. Keys are not standardized (for now).
        """
        # current_user = session.query(User).get(user_id)
        # assert (
        #    current_user is not None and current_user.status == UserStatus.active.value
        # )
        current_user: User = RightsBO.get_user_throw(ro_session, user_id)
        prefs_for_proj: UserPreferences = (
            current_user.preferences_for_projects.filter_by(
                project_id=project_id
            ).first()
        )
        if prefs_for_proj:
            all_prefs_for_proj = json.loads(prefs_for_proj.json_prefs)
        else:
            all_prefs_for_proj = dict()
        return all_prefs_for_proj.get(key, "")

    @staticmethod
    def set_preferences_per_project(
        session: Session, user_id: int, project_id: int, key: str, value: Any
    ):
        """
        Set preference for a key, for given project and user. The key disappears if set to empty string.
        """
        # current_user = session.query(User).get(user_id)
        # assert (
        #    current_user is not None and current_user.status == UserStatus.active.value
        # )
        current_user: User = RightsBO.get_user_throw(session, user_id)
        prefs_for_proj: UserPreferences = (
            current_user.preferences_for_projects.filter_by(
                project_id=project_id
            ).first()
        )
        if prefs_for_proj:
            all_prefs_for_proj = json.loads(prefs_for_proj.json_prefs)
        else:
            prefs_for_proj = UserPreferences()
            prefs_for_proj.project_id = project_id
            prefs_for_proj.user_id = user_id
            session.add(prefs_for_proj)
            all_prefs_for_proj = dict()
        all_prefs_for_proj[key] = value
        if value == "":
            del all_prefs_for_proj[key]
        prefs_for_proj.json_prefs = json.dumps(all_prefs_for_proj)
        logger.info(
            "for %s and %d: %s",
            current_user.name,
            project_id,
            prefs_for_proj.json_prefs,
        )
        session.commit()

    CLASSIF_MRU_KEY: Final = "mru"
    NB_MRU_KEPT: Final = 10

    @classmethod
    def merge_mru(
        cls, before: ClassifIDListT, incoming: ClassifIDListT
    ) -> ClassifIDListT:
        """
        Update recently used list.
        """
        bef_tbl = {
            classif_id: pos_in_mru + 1 for pos_in_mru, classif_id in enumerate(before)
        }
        inc_tbl = {
            classif_id: -pos_hist for pos_hist, classif_id in enumerate(incoming)
        }
        bef_tbl.update(inc_tbl)
        ret = [
            classif_id
            for classif_id in sorted(bef_tbl.keys(), key=lambda v: bef_tbl[v])
        ]
        return ret[: cls.NB_MRU_KEPT]

    @classmethod
    def get_mru(cls, session: Session, user_id: int, project_id: int) -> ClassifIDListT:
        """
        Return classification MRU, with a default of empty list.
        """
        ret = cls.get_preferences_per_project(
            session, user_id, project_id, cls.CLASSIF_MRU_KEY
        )
        if not ret:
            ret = []
        return ret

    @classmethod
    def set_mru(
        cls, session: Session, user_id: int, project_id: int, mru: ClassifIDListT
    ):
        """
        Set classification MRU.
        """
        cls.set_preferences_per_project(
            session, user_id, project_id, cls.CLASSIF_MRU_KEY, mru
        )

    @classmethod
    def validate_usr(
        cls, session: Session, user_model: Any, verify_password: bool = False
    ) -> None:
        """
        Validate basic rules on a user model before setting it into DB.
        TODO: Not done in pydantic, as there are non-complying values in the DB and that would prevent reading them.
        """
        # name & email are mandatory by DB constraints and therefore made so by pydantic model
        errors: List[str] = []
        for a_field in ("name", "email", "organisation", "country"):
            val = getattr(user_model, a_field)
            if val is None:
                continue
            val = val.strip()
            if len(val) <= 3:
                errors.append("%s is too short, 3 chars minimum" % a_field)
        # can check is password is strong  if password not None
        if verify_password == True:
            from helpers.httpexception import DETAIL_PASSWORD_STRENGTH_ERROR

            new_password = getattr(user_model, User.password.name)
            if new_password not in ("", None) and not cls.is_strong_password(
                new_password
            ):
                errors.append(DETAIL_PASSWORD_STRENGTH_ERROR)

        assert not errors, errors

    @staticmethod
    def is_strong_password(password: str) -> bool:
        import re

        match = re.match(USER_PWD_REGEXP, password)
        return bool(match)


@dataclass()
class MinimalUserBO:
    id: UserIDT
    name: str


MinimalUserBOListT = List[MinimalUserBO]


@dataclass()
class UserActivity:
    id: UserIDT
    nb_actions: int
    last_annot: str


UserActivityListT = List[UserActivity]


@dataclass()
class ContactUserBO:
    id: UserIDT
    email: str
    name: str
    orcid: str
    organisation: str


ContactUserListT = List[ContactUserBO]
