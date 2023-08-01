# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, List, Any

from API_models.crud import (
    UserModelWithRights,
    MinUserModel,
    ProjectSummaryModel,
    ResetPasswordReq,
)
from BO.Classification import ClassifIDListT
from BO.Preferences import Preferences
from BO.Rights import RightsBO, NOT_AUTHORIZED
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
    UserValidationService,
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
        try:
            with UserValidationService() as sce:
                self.validation_service: Optional[UserValidationService] = sce
                self.verify_email = sce.email_verification
        except:
            self.validation_service = None
            self.verify_email = False

    # Configuration keys TODO

    ADMIN_UPDATABLE_COLS = [
        User.email,
        User.password,
        User.name,
        User.organisation,
        User.active,
        User.country,
        User.usercreationreason,
    ]
    COMMON_UPDATABLE_COLS = [
        User.email,
        User.password,
        User.name,
        User.organisation,
        User.active,
        User.country,
        User.usercreationreason,
    ]
    EXCLUDE_KEYS = ["password", "last_used_projects", "can_do"]
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
            recaptcha_secret, recaptcha_id = str(
                self.config.get_cnf("RECAPTCHASECRET") or ""
            ), str(self.config.get_cnf("RECAPTCHAID") or "")
            recaptcha = ReCAPTCHAClient(recaptcha_secret, recaptcha_id)
            recaptcha.verify_captcha(no_bot)
            # No right at all
            actions = None
            # verify if the email already in the db
            if self.email_exists(new_user.email):
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Item found",
                )
            if self.validation_service and self.verify_email:
                waitfor = self.validation_service.request_email_verification(
                    new_user.email,
                    action=ACTIVATION_ACTION_CREATE,
                    id=-1,
                    bypass=(new_user.name != ""),
                )
                if waitfor:
                    logger.info(
                        "User create : requested email verification '%s'"
                        % new_user.email
                    )
                    return -1
            new_user.active = self._keep_active()
        else:
            if self.email_exists(new_user.email):
                logger.info("User create : exists '%s'" % new_user.email)
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Item found",
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
            else:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, detail=NOT_AUTHORIZED
                )

        usr = User()
        self.session.add(usr)
        self._model_to_db(
            user_to_update=usr,
            update_src=new_user,
            cols_for_upd=self.ADMIN_UPDATABLE_COLS,
            actions=actions,
        )
        # if user has to be validated by external service
        if self.validation_service is not None and self.verify_email and not usr.active:
            self.validation_service.request_activate_user(
                usr, action=ACTIVATION_ACTION_CREATE
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

        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        if current_user is None:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=NOT_AUTHORIZED)
        user_to_update: Optional[User] = self.session.query(User).get(user_id)
        if user_to_update is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="not found"
            )

        # if email is modified check,if it belongs to another user
        activestate = user_to_update.active
        if update_src.email != user_to_update.email:
            if self.email_exists(update_src.email):
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Item should not be found",
                )
            # if mail changed and validation required -> change the user active value
            if (
                self.validation_service is not None
                and self.verify_email
                and not self._keep_active(current_user)
            ):
                update_src.active = False
                major_data_changed = True

        if current_user.has_role(Role.APP_ADMINISTRATOR) or current_user.has_role(
            Role.USERS_ADMINISTRATOR
        ):
            cols_for_upd = self.ADMIN_UPDATABLE_COLS
            actions = update_src.can_do

        elif current_user.id == user_id:
            cols_for_upd = self.COMMON_UPDATABLE_COLS
            actions = None

        else:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail=NOT_AUTHORIZED
            )
        self._model_to_db(user_to_update, update_src, cols_for_upd, actions)
        # if the email has changed or the account has been deactivated
        if self.validation_service is None:
            return
        if major_data_changed:
            self.validation_service.request_email_verification(
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
            self.validation_service.inform_user_activestate(user_to_update)

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

    # add-ons for mail verification and reset password
    def _is_strong_password(self, password: str) -> bool:
        import re

        special_chars = "[_@$]"
        if len(password) >= 8:
            if (
                re.search("[a-z]", password)
                and re.search("[A-Z]", password)
                and re.search("[0-9]", password)
                and re.search(special_chars, password)
                and not re.search("\s", password)
            ):
                return True
        return False

    def _model_to_db(
        self,
        user_to_update: User,
        update_src: UserModelWithRights,
        cols_for_upd,
        actions,
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
                    # if not self._is_strong_password(new_val):
                    #   raise HTTPEception(status_code= HTTP_422_UNPROCESSABLE_ENTITY, detail="password strength")
                    with LoginService() as sce:
                        new_val = sce.hash_password(new_val)

            setattr(user_to_update, col_name, new_val)
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

    def email_exists(self, email) -> dict:
        return self.ro_session.query(User).filter(User.email == email).scalar() != None

    def _keep_active(self, current_user: Optional[User] = None) -> bool:
        if self.validation_service is None:
            return True
        else:
            # check if required to change active state of user for revalidation
            keepactive = self.validation_service.keepactive()
            if keepactive or (
                current_user is not None
                and (
                    current_user.has_role(Role.APP_ADMINISTRATOR)
                    or current_user.has_role(Role.USERS_ADMINISTRATOR)
                )
            ):
                return True
            else:
                return keepactive

    def _get_active_user_by_email(self, email: str) -> Optional[User]:
        qry = (
            self.ro_session.query(User).filter(User.email == email).filter(User.active)
        )
        users = qry.all()
        if len(users) == 1:
            return users[0]
        return None

    # user activation after validation - can be accessed by a normal user with a token ()
    def activate_user(
        self,
        current_user_id: UserIDT,
        user_id: UserIDT,
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> None:
        """
        Activate a user, anybody if I'm an app admin or user admin. Can be a user with a token when desactivated after email modification.
        TODO : move to UserValidation when Users model and "crud ops" are normalized
        """

        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        if current_user is None or not current_user.active:
            # Unauthenticated user ask for account activation
            # Verify not a robot
            recaptcha_secret, recaptcha_id = str(
                self.config.get_cnf("RECAPTCHASECRET") or ""
            ), str(self.config.get_cnf("RECAPTCHAID") or "")
            recaptcha = ReCAPTCHAClient(recaptcha_secret, recaptcha_id)
            recaptcha.verify_captcha(no_bot)
            if self.validation_service is None:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Service not active"
                )
            err = True
            if token:
                user_id = self.validation_service.get_id_from_token(token)
                if user_id != -1:
                    usr: Optional[User] = self.session.query(User).get(user_id)
                    if usr is not None:
                        err = False
                        self.validation_service.request_activate_user(
                            usr, token=token, action=ACTIVATION_ACTION_UPDATE
                        )
            if err:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=NOT_AUTHORIZED
                )
        elif user_id != -1 and (
            current_user.has_role(Role.APP_ADMINISTRATOR)
            or current_user.has_role(Role.USERS_ADMINISTRATOR)
        ):

            inactive_user: Optional[User] = self.session.query(User).get(user_id)

            if inactive_user is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=NOT_AUTHORIZED
                )
            elif not inactive_user.active:
                cols_for_upd = [User.active]
                update_src = UserModelWithRights(**inactive_user.__dict__)
                update_src.active = True
                self._model_to_db(inactive_user, update_src, cols_for_upd, actions=None)
                if self.validation_service is not None:
                    self.validation_service.inform_user_activestate(inactive_user)
        else:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=NOT_AUTHORIZED)

    def reset_user_password(
        self,
        current_user_id: Optional[UserIDT],
        resetreq: ResetPasswordReq,
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> UserIDT:

        """
        Reset a user password by creating a token and temporary password then sending the informations and update the modified password.
        TODO : move to UserValidation when Users model and "crud ops" are normalized
        """

        # active only with a validation_service
        if self.validation_service is None:
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

            recaptcha_secret, recaptcha_id = str(
                self.config.get_cnf("RECAPTCHASECRET") or ""
            ), str(self.config.get_cnf("RECAPTCHAID") or "")
            recaptcha = ReCAPTCHAClient(recaptcha_secret, recaptcha_id)
            recaptcha.verify_captcha(no_bot)
            # verify if the email exists  in the db
            if not token:
                if not self.email_exists(resetreq.email):
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Item not found",
                    )
        elif not (
            current_user.has_role(Role.APP_ADMINISTRATOR)
            or current_user.has_role(Role.USERS_ADMINISTRATOR)
        ):
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail=NOT_AUTHORIZED
            )

        if token:
            if resetreq.password is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="No password "
                )
            email = self.validation_service.get_email_from_token(token)

            temp_password = self.validation_service.get_reset_from_token(token)
            user_id = self.validation_service.get_id_from_token(token)
            err = True
            if temp_password is not None and user_id != -1:
                user_to_reset: Optional[User] = self.ro_session.query(User).get(user_id)
                if user_to_reset is not None:
                    # find temporary password
                    temp = self.ro_session.query(TempPasswordReset).get(user_id)
                    if temp is not None:
                        verified = self.validation_service.verify_temp_password(
                            str(temp_password), temp
                        )
                        if verified:
                            update_src = UserModelWithRights(**user_to_reset.__dict__)
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
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="Not found"
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
                        self.validation_service.request_reset_password(
                            user_ask_reset, temp_password=temp_password
                        )
                    err = False
                    id = -1
            if err:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="Not found"
                )
            return id
