# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, List, Any

from API_models.crud import UserModelWithRights
from BO.Classification import ClassifIDListT
from BO.Preferences import Preferences
from BO.Rights import RightsBO, NOT_AUTHORIZED
from BO.User import UserBO, UserIDT, UserIDListT
from DB.Project import ProjectIDT
from DB.User import User, Role, UserRole
from helpers.DynamicLogs import get_logger
from providers.Google import ReCAPTCHAClient
from ..helpers.Service import Service

logger = get_logger(__name__)


class UserService(Service):
    """
        Basic CRUD API_operations on User
    """
    # Configuration keys TODO

    ADMIN_UPDATABLE_COLS = [User.email, User.password, User.name, User.organisation, User.active, User.country,
                            User.usercreationdate, User.usercreationreason]

    def create_user(self, current_user_id: Optional[UserIDT], new_user: UserModelWithRights,
                    no_bot: List[str]) -> UserIDT:
        if current_user_id is None:
            # Unauthenticated user tries to create an account
            # Verify not a robot
            captcha_secret, captcha_id = self.config.get("RECAPTCHASECRET"), self.config.get('RECAPTCHAID')
            if captcha_secret and captcha_id:
                # Basic verification on input
                assert no_bot is not None, "reCaptcha verif needs data"
                assert len(no_bot) == 2, 'invalid no_bot'
                for a_str in no_bot:
                    assert len(a_str) < 512, 'invalid no_bot'
                verifier = ReCAPTCHAClient(captcha_id, captcha_secret)
                error = verifier.validate(no_bot[0], no_bot[1])
                assert error is None, error
            # No right at all
            actions = None
        else:
            # Must be admin to create an account
            current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
            assert current_user is not None
            assert current_user.has_role(Role.APP_ADMINISTRATOR), NOT_AUTHORIZED
            actions = new_user.can_do
        same_email_user = self.ro_session.query(User).filter(User.email == new_user.email).scalar()  # type:ignore
        assert same_email_user is None, ["email already corresponds to another user"]
        same_name_user = self.ro_session.query(User).filter(User.name == new_user.name).scalar()  # type:ignore
        assert same_name_user is None, ["name already corresponds to another user"]
        usr = User()
        self.session.add(usr)
        self._model_to_db(updated_user=usr, update_src=new_user,
                          cols_for_upd=self.ADMIN_UPDATABLE_COLS, actions=actions)
        return usr.id

    def update_user(self, current_user_id: UserIDT, user_id: UserIDT, update_src: UserModelWithRights) -> None:
        """
            Update a user, who can be myself or anybody if I'm an app admin.
        """
        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        assert current_user is not None
        updated_user: Optional[User] = self.session.query(User).get(user_id)
        assert updated_user is not None
        assert updated_user.id == user_id
        if current_user.has_role(Role.APP_ADMINISTRATOR):
            cols_for_upd = self.ADMIN_UPDATABLE_COLS
            actions = update_src.can_do
        elif current_user.id == user_id:
            cols_for_upd = [User.name, User.password]
            actions = None
        else:
            assert False, NOT_AUTHORIZED
        self._model_to_db(updated_user, update_src, cols_for_upd, actions)

    def search_by_id(self, current_user_id: UserIDT, user_id: UserIDT) -> Optional[User]:
        # TODO: Not consistent with others e.g. project.query()
        ret = self.ro_session.query(User).get(user_id)
        return ret

    def get_full_by_id(self, current_user_id: UserIDT, user_id: UserIDT) -> UserModelWithRights:
        db_usr = self.ro_session.query(User).get(user_id)
        assert db_usr is not None
        ret = self._get_full_user(db_usr)
        return ret

    def _get_full_user(self, db_usr: User) -> UserModelWithRights:
        ret = UserModelWithRights.from_orm(db_usr)  # type:ignore
        ret.last_used_projects = Preferences(db_usr).recent_projects(session=self.session)  # type:ignore
        ret.can_do = RightsBO.get_allowed_actions(db_usr)  # type:ignore
        ret.password = "?"  # type:ignore
        return ret

    def search(self, current_user_id: UserIDT, by_name: Optional[str]) -> List[User]:
        qry = self.ro_session.query(User).filter(User.active)
        if by_name is not None:
            qry = qry.filter(User.name.ilike(by_name))
        else:
            return []
        return [a_rec for a_rec in qry]

    def _get_users_with_role(self, role: str) -> List[User]:
        qry = self.ro_session.query(User)
        qry = qry.join(UserRole)
        qry = qry.join(Role)
        qry = qry.filter(User.active)
        qry = qry.filter(Role.name == role)
        return [a_rec for a_rec in qry]

    def get_users_admins(self) -> List[User]:
        """
            List persons with the USERS_ADMINISTRATOR role.
        """
        return self._get_users_with_role(Role.USERS_ADMINISTRATOR)

    def get_admin_users(self, current_user_id: UserIDT) -> List[User]:
        """
            List persons with the APP_ADMINISTRATOR role.
        """
        return self._get_users_with_role(Role.APP_ADMINISTRATOR)

    def list(self, current_user_id: UserIDT, user_ids: UserIDListT) -> List[UserModelWithRights]:
        """
            List all users, or some of them by their ids, if requester is admin.
        """
        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)

        assert current_user is not None
        ret = []
        if current_user.has_role(Role.APP_ADMINISTRATOR):
            qry = self.ro_session.query(User)
            if len(user_ids) > 0:
                qry = qry.filter(User.id.in_(user_ids))
            for db_usr in qry:
                ret.append(self._get_full_user(db_usr))
        return ret

    def get_preferences_per_project(self, user_id: UserIDT, project_id: ProjectIDT, key: str) -> Any:
        """
            Get a preference, for given project and user. Keys are not standardized (for now).
        """
        return UserBO.get_preferences_per_project(self.session, user_id, project_id, key)

    def set_preferences_per_project(self, user_id: UserIDT, project_id: ProjectIDT, key: str, value: Any):
        """
            Set preference for a key, for given project and user. The key disappears if set to empty string.
        """
        UserBO.set_preferences_per_project(self.session, user_id, project_id, key, value)

    def update_classif_mru(self, user_id: UserIDT, project_id: ProjectIDT, last_used: ClassifIDListT):
        """
            Update recently used list for the user+project.
            :param user_id:
            :param project_id:
            :param last_used: The used classif_id, in time order, i.e. recents are in last. No guarantee
                    of uniqueness inside the list.
        """
        mru = UserBO.get_mru(self.session, user_id, project_id)
        mru = UserBO.merge_mru(mru, last_used)
        UserBO.set_mru(self.session, user_id, project_id, mru)

    def _model_to_db(self, updated_user: User, update_src: UserModelWithRights, cols_for_upd, actions):
        """
            Transfer model values into the DB record.
        """
        UserBO.validate_usr(self.session, update_src)
        # Do the in-memory update
        for a_col in cols_for_upd:
            col_name = a_col.name  # type:ignore
            new_val = getattr(update_src, col_name)
            if a_col == User.password and new_val in ("", None):
                # By policy, don't clear passwords
                continue
            setattr(updated_user, col_name, new_val)
        if actions is not None:
            # Set roles so that requested actions will be possible
            all_roles = {a_role.name: a_role for a_role in self.session.query(Role)}
            RightsBO.set_allowed_actions(updated_user, actions, all_roles)  # type:ignore
        # Commit on DB
        self.session.commit()

    def search_organizations(self, name: str) -> List[str]:
        """
            Return the already-used org names with given pattern.
        """
        qry = self.ro_session.query(User.organisation).distinct()
        qry = qry.filter(User.organisation.ilike(name))
        return [r for r, in qry.all() if r is not None]
