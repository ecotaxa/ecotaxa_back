# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, Union, List, Any

from API_models.crud import (
    UserModelWithRights,
    MinUserModel,
    ProjectSummaryModel,
    UserModelProfile,
    ResetPasswordReq,
)
from BO.Classification import ClassifIDListT
from BO.Preferences import Preferences
from BO.Rights import RightsBO, NOT_AUTHORIZED, NOT_FOUND
from BO.User import UserBO, UserIDT, UserIDListT
from DB.Project import ProjectIDT
from DB.User import User, Role, UserRole, TempPasswordReset
from helpers.DynamicLogs import get_logger
from helpers.pydantic import BaseModel, Field
from helpers.login import LoginService
from providers.Google import ReCAPTCHAClient
from ..helpers.Service import Service
from fastapi import HTTPException
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_403_FORBIDDEN,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)
from ..helpers.UserValidation import (
    UserValidation,
    ACTIVATION_ACTION_CREATE,
    ACTIVATION_ACTION_UPDATE,
)


logger = get_logger(__name__)


class TempPasswordModel(BaseModel):
    user_id: int = Field(
        title="User Id", description="Internal, numeric id of the user.", example=1
    )
    temp_password: str = Field(
        title="Temporary password",
    )


class UserService(Service):
    """
    Basic CRUD API_operations on User
    """

    def __init__(self) -> None:
        super().__init__()
        self._uservalidation = UserValidation()

    # Configuration keys TODO

    ADMIN_UPDATABLE_COLS = [
        User.email,
        User.password,
        User.name,
        User.active,
        User.organisation,
        User.country,
        User.usercreationreason,
    ]
    COMMON_UPDATABLE_COLS = [
        User.email,
        User.password,
        User.name,
        User.organisation,
        User.country,
        User.usercreationreason,
    ]

    EXCLUDE_KEYS = ["password", "last_used_projects", "can_do"]
    EMPTY_MAIL_STATUS = " "
    WAIT_MAIL_STATUS = "W"
    VALID_MAIL_STATUS = "V"
    # check context to know if the email has to be verifed

    def create_user(
        self,
        current_user_id: Optional[UserIDT],
        new_user: UserModelWithRights,
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> UserIDT:
        if current_user_id is None:
            # Unauthenticated user tries to create an account
            # Verify not a robot
            self._verify_captcha(no_bot)
            # No right at all
            actions = None
            # verify if the email already in the db
            self._has_ident_user(
                dict({"email": new_user.email, "name": new_user.name}), False
            )
            bypass = new_user.name != ""
            # request email verification if  validation is on
            if self._uservalidation:
                waitfor = self._uservalidation.request_email_verification(
                    new_user.email,
                    action=ACTIVATION_ACTION_CREATE,
                    id=-1,
                    bypass=bypass,
                )
                if waitfor:
                    logger.info(
                        "User create : requested email verification '%s'"
                        % new_user.email
                    )
                    return -1
                new_user.active = self._keep_active()
        else:
            self._has_ident_user(
                dict({"email": new_user.email, "name": new_user.name}), False
            )
            # Must be admin to create an account
            current_user: Optional[User] = self.ro_session.query(User).get(
                current_user_id
            )
            if current_user is None:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail=NOT_AUTHORIZED
                )
            if current_user.has_role(Role.APP_ADMINISTRATOR) or current_user.has_role(
                Role.USERS_ADMINISTRATOR
            ):
                actions = new_user.can_do
                # validation only by external user admin - other admins can add but not activate
                new_user.active = self._keep_active(current_user)
            else:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, detail=NOT_AUTHORIZED
                )

        usr = User()
        self.session.add(usr)
        self._model_to_db(
            usr,
            new_user,
            self.ADMIN_UPDATABLE_COLS,
            actions=actions,
        )
        # if user has to be validated by external service
        if self._uservalidation and not usr.active:
            user_profile = UserModelProfile.from_orm(usr)
            self._uservalidation.request_activate_user(
                user_profile, action=ACTIVATION_ACTION_CREATE
            )
        logger.info("User created :  '%s'" % new_user.email)
        return usr.id

    def update_user(
        self,
        current_user_id: UserIDT,
        user_id: UserIDT,
        update_src: UserModelWithRights,
    ) -> None:
        """
        Update a user, who can be myself or anybody if I'm an app admin.
        """
        major_data_changed = False
        mail_status = None
        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        if current_user is None:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=NOT_AUTHORIZED)
        user_to_update: Optional[User] = self.session.query(User).get(user_id)
        if user_to_update is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=NOT_FOUND
            )

        activestate = update_src.active = user_to_update.active
        # if email or name is modified check,if it belongs to another user
        if (
            update_src.email != user_to_update.email
            or update_src.name != user_to_update.name
        ):
            self._has_ident_user(
                dict(
                    {
                        "email": update_src.email,
                        "name": update_src.name,
                    }
                ),
                False,
                user_to_update.id,
            )
            if self._uservalidation and not self._keep_active(current_user):
                major_data_changed = True
                update_src.active = False
                # reset the mail_status
                mail_status = self.EMPTY_MAIL_STATUS

        if self._current_is_admin(current_user):
            cols_for_upd = self.ADMIN_UPDATABLE_COLS
            actions = update_src.can_do

        elif current_user.id == user_id:
            cols_for_upd = self.COMMON_UPDATABLE_COLS
            actions = None
        else:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail=NOT_AUTHORIZED
            )
        self._model_to_db(
            user_to_update, update_src, cols_for_upd, actions, mail_status=mail_status
        )
        # if the email has changed or the account has been deactivated
        # if not self._uservalidation:
        #    return
        if self._uservalidation and major_data_changed:
            self._uservalidation.request_email_verification(
                user_to_update.email,
                action=ACTIVATION_ACTION_UPDATE,
                id=user_to_update.id,
            )
            logger.info(
                "User email modified : requested verification '%s'"
                % user_to_update.email
            )
        elif activestate != update_src.active:
            # inform the user if its account is desactivated and the validation service is active
            user_profile = UserModelProfile.from_orm(user_to_update)
            self._uservalidation.inform_user_activestate(user_profile)

    def search_by_id(
        self, current_user_id: UserIDT, user_id: UserIDT
    ) -> Optional[User]:
        # TODO: Not consistent with others e.g. project.query()
        ret = self.ro_session.query(User).get(user_id)
        return ret

    def get_full_by_id(
        self, current_user_id: UserIDT, user_id: UserIDT
    ) -> UserModelWithRights:
        db_usr = self.ro_session.query(User).get(user_id)
        if db_usr is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Item not found")
        else:
            ret = self._get_full_user(db_usr)
        return ret

    def _get_full_user(self, db_usr: User) -> UserModelWithRights:
        ret = UserModelWithRights.from_orm(db_usr)
        mru_projs = Preferences(db_usr).recent_projects(session=self.ro_session)
        ret.last_used_projects = [
            ProjectSummaryModel(projid=prj_id, title=prj_title)
            for prj_id, prj_title in mru_projs
        ]
        ret.can_do = [act.value for act in RightsBO.get_allowed_actions(db_usr)]
        ret.password = "?"
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

    def list(
        self,
        current_user_id: UserIDT,
        user_ids: UserIDListT,
        minimize: Optional[str] = None,
    ) -> List[UserModelWithRights]:
        """
        List all users, or some of them by their ids, if requester is admin.
        """
        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)

        if current_user is None:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=NOT_AUTHORIZED)
        ret = []
        if current_user.has_role(Role.APP_ADMINISTRATOR) or current_user.has_role(
            Role.USERS_ADMINISTRATOR
        ):
            qry = self.ro_session.query(User)
            if len(user_ids) > 0:
                qry = qry.filter(User.id.in_(user_ids))

            for db_usr in qry:
                ret.append(self._get_full_user(db_usr))
        return ret

    def get_preferences_per_project(
        self, user_id: UserIDT, project_id: ProjectIDT, key: str
    ) -> Any:
        """
        Get a preference, for given project and user. Keys are not standardized (for now).
        """
        return UserBO.get_preferences_per_project(
            self.session, user_id, project_id, key
        )

    def set_preferences_per_project(
        self, user_id: UserIDT, project_id: ProjectIDT, key: str, value: Any
    ) -> None:
        """
        Set preference for a key, for given project and user. The key disappears if set to empty string.
        """
        UserBO.set_preferences_per_project(
            self.session, user_id, project_id, key, value
        )

    def update_classif_mru(
        self, user_id: UserIDT, project_id: ProjectIDT, last_used: ClassifIDListT
    ) -> None:
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

    def _model_to_db(
        self,
        user_to_update: User,
        update_src: UserModelWithRights,
        cols_for_upd,
        actions,
        mail_status: Optional[str] = None,
    ) -> None:
        """
        Transfer model values into the DB record.
        """
        UserBO.validate_usr(self.session, update_src)
        # Do the in-memory update
        for a_col in cols_for_upd:
            col_name = a_col.name
            new_val = getattr(update_src, col_name)
            if a_col == User.password:
                if new_val in ("", None):
                    # By policy, don't clear passwords
                    continue
                else:
                    # can check is password is strong
                    # if not UserBO.is_strong_password(new_val):
                    #   raise HTTPEception(status_code= HTTP_422_UNPROCESSABLE_ENTITY, detail="password strength")
                    with LoginService() as sce:
                        new_val = sce.hash_password(new_val)

            setattr(user_to_update, col_name, new_val)
        if mail_status is not None and mail_status != user_to_update.mail_status:
            import time

            setattr(user_to_update, str(User.mail_status), mail_status)
            setattr(user_to_update, str(User.mail_status_date), time.time())

        if actions is not None:
            # Set roles so that requested actions will be possible
            all_roles = {a_role.name: a_role for a_role in self.session.query(Role)}
            RightsBO.set_allowed_actions(user_to_update, actions, all_roles)
        # Commit on DB
        self.session.commit()

    def search_organizations(self, name: str) -> List[str]:
        """
        Return the already-used org names with given pattern.
        """
        qry = self.ro_session.query(User.organisation).distinct()
        qry = qry.filter(User.organisation.ilike(name))
        return [r for r, in qry if r is not None]

    def _has_ident_user(self, userdata: dict, valid: bool, id: int = -1) -> None:
        """
        Exception if the mail and/or name exists and valid is False or the mail and/or name does not exists and valid is True
        """
        qry = self.ro_session.query(User)
        if id != -1:
            qry = qry.filter(User.id != id)
        is_other = False
        if "email" in userdata.keys():
            is_other = qry.filter(User.email == userdata["email"]).scalar() != None
        if is_other and not valid:
            detail = ["email already corresponds to another user"]
        elif "name" in userdata.keys():
            is_other = qry.filter(User.name == userdata["name"]).scalar() != None
            if is_other and not valid:
                detail = ["name already corresponds to another user"]
            else:
                detail = [NOT_FOUND]
        elif is_other != valid:
            detail = [NOT_FOUND]
        if is_other != valid:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )

    def _keep_active(self, current_user: Optional[User] = None) -> bool:
        # check if required to change active state of user for revalidation
        if self._uservalidation is None:
            return True
        is_admin = self._current_is_admin(current_user)
        if current_user is None:
            email = None
        else:
            email = current_user.email
        return self._uservalidation.keep_active(email, is_admin)

    def _get_active_user_by_email(self, email: str) -> Optional[User]:
        qry = (
            self.ro_session.query(User).filter(User.email == email).filter(User.active)
        )
        users = qry.all()
        if len(users) == 1:
            return users[0]
        return None

    def set_activestate_user(
        self,
        user_id: UserIDT,
        current_user_id: Optional[UserIDT],
        no_bot: Optional[List[str]],
        token: Optional[str],
        reason: Optional[str],
    ) -> None:
        if current_user_id is None and (
            (reason is None and token is None) or reason is not None
        ):
            HTTPException(status_code=HTTP_403_FORBIDDEN, detail=[NOT_AUTHORIZED])
        if reason is None:
            self.activate_user(
                user_id, current_user_id=current_user_id, no_bot=no_bot, token=token
            )
        elif current_user_id is not None:
            self._discard_user(user_id, reason=reason, current_user_id=current_user_id)

    # user activation after validation - can be accessed by a normal user with a token ()

    def activate_user(
        self,
        user_id: UserIDT,
        current_user_id: Optional[UserIDT],
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> None:
        """
        Activate a user, anybody if I'm an app admin or user admin. Can be a user - who has been desactivated after email modification - with a token .
        TODO : move to _uservalidation when Users model and "crud ops" are normalized
        """

        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        if current_user is None or not current_user.active:
            # Unauthenticated user ask for account activation
            # Verify not a robot
            self._verify_captcha(no_bot)
            if not self._uservalidation:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail=["Service not active"]
                )
            err = True
            if token:
                user_id = self._uservalidation.get_id_from_token(token)
                if user_id != -1:
                    usr: Optional[User] = self.session.query(User).get(user_id)
                    if usr is not None:
                        err = False
                        user_profile = UserModelProfile.from_orm(usr)
                        self._uservalidation.request_activate_user(
                            user_profile,
                            token=token,
                            action=ACTIVATION_ACTION_UPDATE,
                        )
            if err:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=NOT_AUTHORIZED
                )
        elif user_id != -1 and self._current_is_admin(current_user):
            inactive_user: Optional[User] = self.session.query(User).get(user_id)
            if inactive_user is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=NOT_AUTHORIZED
                )
            elif not inactive_user.active:
                cols_for_upd = [User.active]
                mail_status = None
                update_src = UserModelWithRights.from_orm(inactive_user)
                update_src.active = True
                if inactive_user.mail_status != self.VALID_MAIL_STATUS:
                    if self._uservalidation and self._current_is_admin(
                        current_user, True
                    ):
                        mail_status = self.VALID_MAIL_STATUS

                self._model_to_db(
                    inactive_user,
                    update_src,
                    cols_for_upd=cols_for_upd,
                    actions=None,
                    mail_status=mail_status,
                )
                if self._uservalidation:
                    user_profile = UserModelProfile.from_orm(inactive_user)
                    self._uservalidation.inform_user_activestate(user_profile)
        else:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=NOT_AUTHORIZED)

    def _discard_user(
        self,
        user_id: UserIDT,
        reason: str,
        current_user_id: UserIDT,
    ) -> None:
        current_user: Optional[User] = self.search_by_id(
            current_user_id, current_user_id
        )
        # only external user admin if external validation is on else user or app admin
        if current_user is None or self._current_is_admin(
            current_user, is_main_admin=True
        ):
            HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=["only user admin can discard"],
            )
        user: Optional[User] = self.search_by_id(current_user_id, user_id)
        # set mail status to wait
        if user is not None:
            update_src = UserModelWithRights.from_orm(user)
            self._model_to_db(
                user,
                update_src,
                [],
                actions=None,
                mail_status=self.WAIT_MAIL_STATUS,
            )
            user_profile = UserModelProfile.from_orm(user)
            self._uservalidation.request_user_to_modify_profile(user_profile, reason)
        HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[NOT_FOUND],
        )

    # check if current_user can admin users
    def _current_is_admin(
        self, current_user: Optional[User], is_main_admin: bool = False
    ) -> bool:
        if current_user is not None:
            is_admin = current_user.has_role(
                Role.APP_ADMINISTRATOR
            ) or current_user.has_role(Role.USERS_ADMINISTRATOR)
            if not is_admin:
                return False
            if is_main_admin:
                if self._uservalidation:
                    return (
                        current_user.email
                        == self._uservalidation.account_activate_email
                    )
            return is_admin
        return False

    # verify temp password before reset
    @staticmethod
    def verify_temp_password(
        temp_password: str, temp: Optional[TempPasswordReset]
    ) -> bool:
        """
        Returns ``True`` if the temporary password is valid for the specified user id.
        :param temp_password: A plaintext password to verify
        :param user id: The user id to verify against
        """
        if temp is None:
            return False
        with LoginService() as sce:
            if sce.use_double_hash(temp.temp_password):
                verified = sce._pwd_context.verify(
                    sce.get_hmac(temp_password), temp.temp_password
                )
            else:
                # Try with plaintext password.
                verified = sce._pwd_context.verify(temp_password, temp.temp_password)
        if not verified:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=NOT_AUTHORIZED,
            )
        return verified

    def _verify_captcha(self, no_bot: Optional[List[str]]) -> None:
        recaptcha_secret, recaptcha_id = str(
            self.config.get_cnf("RECAPTCHASECRET") or ""
        ), str(self.config.get_cnf("RECAPTCHAID") or "")
        recaptcha = ReCAPTCHAClient(recaptcha_secret, recaptcha_id)
        recaptcha.verify_captcha(no_bot)

    @staticmethod
    def _is_strong_password(password: str) -> bool:
        import re

        special_chars = "[_@$]"
        if len(password) >= 8:
            if (
                re.search("[a-z]", password)
                and re.search("[A-Z]", password)
                and re.search("[0-9]", password)
                and re.search(special_chars, password)
                # and not re.search("\s", password)
            ):
                return True
        return False

    def reset_password(
        self,
        current_user_id: Optional[UserIDT],
        resetreq: ResetPasswordReq,
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> UserIDT:
        """
        Reset a user password by creating a token and temporary password then sending the informations and update the modified password.
        TODO : move to _uservalidation when Users model and "crud ops" are normalized
        """
        # active only when validation is on
        if not self._uservalidation:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN)
        if current_user_id is not None:
            current_user: Optional[User] = self.ro_session.query(User).get(
                current_user_id
            )
        else:
            current_user = None
        if current_user is None:
            # Unauthenticated user asks to reset his password
            # Verify not a robot
            self._verify_captcha(no_bot)
            # verify if the email exists  in the db
            if token is None:
                self._has_ident_user(dict({"email": resetreq.email}), True)
        # if authenticated must be admin to request the reset
        elif not self._current_is_admin(current_user):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail=NOT_AUTHORIZED
            )
        id = -1
        if token:
            if resetreq.password is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=["No password "]
                )

            email = self._uservalidation.get_email_from_token(token)
            temp_password = self._uservalidation.get_reset_from_token(token)
            user_id = self._uservalidation.get_id_from_token(token)
            err = True
            if temp_password is not None and user_id != -1:
                user_to_reset: Optional[User] = self.ro_session.query(User).get(user_id)
                if user_to_reset is not None:
                    # find temporary password
                    temp = self.ro_session.query(TempPasswordReset).get(user_id)
                    if temp is not None:
                        verified = self.verify_temp_password(str(temp_password), temp)
                        if verified:
                            update_src = UserModelWithRights.from_orm(user_to_reset)
                            update_src.password = resetreq.password
                            self._model_to_db(
                                user_to_reset,
                                update_src,
                                [User.password],
                                actions=None,
                            )
                            # remove temp_user_reset row
                            temp_pw: Optional[
                                TempPasswordReset
                            ] = self.ro_session.query(TempPasswordReset).get(
                                user_to_reset.id
                            )
                            self.session.delete(temp_pw)
                            self.session.commit()
                            id = user_to_reset.id
                            err = False
            if err:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=NOT_FOUND
                )

        else:
            # store a temporary unique password in the db for the user_id
            err = True
            email = str(resetreq.email or "")
            if email != "":
                user_ask_reset: Optional[User] = self._get_active_user_by_email(email)
                if user_ask_reset is not None:
                    import uuid

                    temp_password = uuid.uuid4().hex
                    with LoginService() as sce:
                        hash_temp_password = sce.hash_password(temp_password)
                        temp_rs: Optional[TempPasswordReset] = self.ro_session.query(
                            TempPasswordReset
                        ).get(user_ask_reset.id)
                    if temp_rs is None:
                        temp_rs = TempPasswordReset(
                            user_id=user_ask_reset.id, temp_password=hash_temp_password
                        )
                        self.session.add(temp_rs)
                        self.session.commit()
                    else:
                        temp_rs.temp_password = hash_temp_password
                        self.session.commit()
                        user_profile = UserModelProfile.from_orm(user_ask_reset)
                        self._uservalidation.request_reset_password(
                            user_profile, temp_password=temp_password
                        )
                    err = False
            if err:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=NOT_FOUND
                )
        return id
