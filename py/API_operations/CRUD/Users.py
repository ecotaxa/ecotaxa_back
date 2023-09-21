# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, List, Any

from API_models.crud import (
    UserModelWithRights,
    ProjectSummaryModel,
    UserModelProfile,
    ResetPasswordReq,
)
from BO.Classification import ClassifIDListT
from BO.Preferences import Preferences
from BO.Rights import RightsBO, NOT_AUTHORIZED, NOT_FOUND
from BO.User import UserBO, UserIDT, UserIDListT, UserStatus, UserStatus
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
    ActivationType,
    SHORT_TOKEN_AGE,
    PROFILE_TOKEN_AGE,
)
from helpers import DateTime
from helpers.httpexception import (
    DETAIL_VALIDATION_NOT_ACTIVE,
    DETAIL_INVALID_PARAMETER,
    DETAIL_PASSWORD_STRENGTH_ERROR,
    DETAIL_CANT_CHECK_VALIDITY,
    DETAIL_INVALID_EMAIL,
    DETAIL_INVALID_STATUS,
    DETAIL_NO_USERS_ADMIN,
    DETAIL_EMAIL_OWNED_BY_OTHER,
    DETAIL_NAME_OWNED_BY_OTHER,
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

    _assistance_email: str = ""
    _validation_emails: List[str] = []

    def __init__(self) -> None:
        super().__init__()
        self._uservalidation: Optional[UserValidation] = None
        verify_email = self.config.get_user_email_verification() == "on"
        account_validation = self.config.get_account_validation() == "on"
        if verify_email or account_validation:
            self._uservalidation = UserValidation()

    # Configuration keys TODO

    ADMIN_UPDATABLE_COLS = [
        User.email,
        User.password,
        User.name,
        User.status,
        User.status_date,
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

    # check context to know if the email has to be verifed

    def create_user(
        self,
        current_user_id: Optional[UserIDT],
        new_user: UserModelWithRights,
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> UserIDT:
        now = DateTime.now_time()
        cols_to_upd = self.ADMIN_UPDATABLE_COLS

        if current_user_id is None:
            # Unauthenticated user tries to create an account
            # Verify not a robot
            self._verify_captcha(no_bot)
            # No right at all
            actions = None
            # request email verification if  validation is on
            if self._uservalidation:
                if token:
                    if new_user.id is not None and new_user.id > 0:
                        return self._modify_new_user(new_user, token)
                    new_user = self._set_mail_status(new_user, True, confirm=True)
                    cols_to_upd.append(User.mail_status)
                    cols_to_upd.append(User.mail_status_date)
                else:
                    # check valid user
                    self._is_valid_user(new_user, -1)
                    bypass = new_user.name != ""
                    if not bypass:
                        new_user = self._set_mail_status(new_user, False, confirm=True)
                        return -1
                new_user.status = int(self._keep_active())
        else:
            # Must be admin to create an account
            current_user: Optional[User] = self.ro_session.query(User).get(
                current_user_id
            )
            if self._current_is_admin(current_user):
                actions = new_user.can_do
                # validation only by external user admin - other admins can add but not activate if set in config
                new_user.status = int(self._keep_active(current_user))
            else:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED, detail=[NOT_AUTHORIZED]
                )
        self._is_valid_user(new_user, -1)
        new_user.status_date = now
        usr = User()
        self.session.add(usr)
        self._model_to_db(
            usr,
            new_user,
            cols_to_upd=cols_to_upd,
            actions=actions,
        )
        # if user has to be validated by external service
        if self._uservalidation and not new_user.status:
            user_profile = UserModelProfile.from_orm(usr)
            self._uservalidation.request_activate_user(
                user_profile,
                validation_emails=self._get_validation_emails(),
                action=ActivationType.create.value,
            )
        logger.info("User created :  '%s'" % new_user.email)

        return usr.id

    def _verify_token(self, new_user: UserModelWithRights, token: str) -> int:
        if not self._uservalidation:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        email = self._uservalidation.get_email_from_token(token)
        user_id = self._uservalidation.get_id_from_token(token)
        if email != new_user.email or user_id != new_user.id:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_INVALID_PARAMETER],
            )
        return new_user.id

    def _modify_new_user(self, new_user: UserModelWithRights, token: str) -> UserIDT:
        """
        user can modify major information before activation
        """
        if not self._uservalidation:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        if not token:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=[NOT_AUTHORIZED],
            )
        user_id = self._verify_token(new_user, token)
        detail = None

        verified = False
        usr: Optional[User] = self.session.query(User).get(user_id)

        if usr is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[NOT_FOUND],
            )

        if usr.status != UserStatus.pending.value:
            detail = ["an active or valid or not checked profile cannot be replaced"]
        else:
            with LoginService() as sce:
                verified = sce.verify_and_update_password(new_user.password, usr)
        if not verified:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=[NOT_AUTHORIZED],
            )

        if detail:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        # token verified,  user found and access verified by email and password - now check compatibility with other users in DB
        self._is_valid_user(new_user, user_id)
        # update a profile with informations requested by the main user admin - status to 0
        cols_to_upd = self.COMMON_UPDATABLE_COLS
        del cols_to_upd[User.password]
        self._update_user_row(
            new_user,
            usr,
            action=ActivationType.update,
            cols_to_upd=cols_to_upd,
            current_user=None,
        )
        logger.info("User profile modified %s :  '%s'" % (new_user.email, user_id))
        return user_id

    def update_user(
        self,
        current_user_id: UserIDT,
        user_id: UserIDT,
        update_src: UserModelWithRights,
    ) -> None:
        """
        Update a user, who can be myself or anybody if I'm an app admin.
        """
        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        if current_user is None:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=[NOT_AUTHORIZED])
        user_to_update: Optional[User] = self.session.query(User).get(user_id)
        if user_to_update is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=[NOT_FOUND]
            )
        self._is_valid_user(update_src, user_to_update.id)

        if self._current_is_admin(current_user):
            cols_to_upd = self.ADMIN_UPDATABLE_COLS

        elif (
            current_user.id == user_id
            and current_user.status == UserStatus.active.value
        ):
            cols_to_upd = self.COMMON_UPDATABLE_COLS
        else:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail=[NOT_AUTHORIZED],
            )
        self._update_user_row(
            update_src,
            user_to_update,
            action=ActivationType.update,
            cols_to_upd=cols_to_upd,
            current_user=current_user,
        )
        logger.info("User profile update %s :  '%s'" % (update_src.email, user_id))

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

    def _get_user_with_rights(self, db_usr: User) -> UserModelWithRights:
        ret = UserModelWithRights.from_orm(db_usr)
        ret.can_do = [act.value for act in RightsBO.get_allowed_actions(db_usr)]
        ret.password = "?"
        return ret

    def search(self, current_user_id: UserIDT, by_name: Optional[str]) -> List[User]:
        qry = self.ro_session.query(User).filter(User.status == UserStatus.active.value)
        if by_name is not None:
            qry = qry.filter(User.name.ilike(by_name))
        else:
            return []
        return [a_rec for a_rec in qry]

    def _get_users_with_role(self, role: str) -> List[User]:
        qry = self.ro_session.query(User)
        qry = qry.join(UserRole)
        qry = qry.join(Role)
        qry = qry.filter(User.status == UserStatus.active.value)
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
    ) -> List[UserModelWithRights]:
        """
        List all users, or some of them by their ids, if requester is admin.
        """
        current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)

        if current_user is None:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=[NOT_AUTHORIZED])
        ret = []
        if self._current_is_admin(current_user):
            # for faster display in test
            # get_user_details = self._get_user_with_rights
            get_user_details = self._get_full_user
            qry = self.ro_session.query(User)
            if len(user_ids) > 0:
                # get_user_details = self._get_full_user
                qry = qry.filter(User.id.in_(user_ids))
            for db_usr in qry:

                ret.append(get_user_details(db_usr))
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
        cols_to_upd,
        actions,
    ) -> None:
        """
        Transfer model values into the DB record.
        """
        UserBO.validate_usr(self.session, update_src)
        # Do the in-memory update
        for a_col in cols_to_upd:
            col_name = a_col.name
            new_val = getattr(update_src, col_name)
            if a_col == User.password:
                if new_val in ("", None):
                    # By policy, don't clear passwords
                    continue
                else:

                    # can check is password is strong
                    if not UserValidation.is_strong_password(new_val):
                        raise HTTPException(
                            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=[DETAIL_PASSWORD_STRENGTH_ERROR],
                        )
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

    def _has_ident_user(self, userdata: dict, valid: bool, id: int = -1) -> None:
        """
        Exception if the mail and/or name exists and valid is False or the mail and/or name does not exists and valid is True
        """
        qry = self.ro_session.query(User)
        if "id" in userdata.keys() and id != userdata["id"]:
            id == userdata["id"]
        if id != -1:
            qry = qry.filter(User.id != id)
        is_other = False
        if "email" in userdata.keys():
            is_other = qry.filter(User.email == userdata["email"]).scalar() != None
        if is_other and not valid:
            detail = [DETAIL_EMAIL_OWNED_BY_OTHER]
        elif "name" in userdata.keys():
            is_other = qry.filter(User.name == userdata["name"]).scalar() != None
            if is_other and not valid:
                detail = [DETAIL_NAME_OWNED_BY_OTHER]
            else:
                detail = [NOT_FOUND]
        elif is_other != valid:
            detail = [NOT_FOUND]
        if is_other != valid:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )

    def _update_user_row(
        self,
        update_src: UserModelWithRights,
        user_to_update: User,
        action: ActivationType,
        cols_to_upd: List,
        current_user: Optional[User],
    ):
        ask_activate = False
        is_admin = self._current_is_admin(current_user)
        status = int(self._keep_active(current_user))
        if self._uservalidation:
            if (
                self._uservalidation.account_validation == True
                and self._is_major_data_change(update_src, user_to_update)
            ):
                status = UserStatus.inactive.value
                ask_activate = True
            if update_src.email != user_to_update.email:
                update_src = self._set_mail_status(
                    update_src,
                    False,
                    confirm=not is_admin,
                    user=user_to_update,
                    action=ActivationType.update,
                )
                cols_to_upd.append(User.mail_status)
                cols_to_upd.append(User.mail_status_date)
        update_src.status = status
        update_src.status_date = DateTime.now_time()
        cols_to_upd.append(User.status)
        cols_to_upd.append(User.status_date)
        if is_admin:
            actions = update_src.can_do
        else:
            actions = None
        self._model_to_db(
            user_to_update,
            update_src,
            cols_to_upd=cols_to_upd,
            actions=actions,
        )
        if self._uservalidation is not None and ask_activate:
            self._uservalidation.request_activate_user(
                UserModelProfile.from_orm(user_to_update),
                validation_emails=self._get_validation_emails(),
                action=ActivationType.update.value,
            )

    def _is_major_data_change(
        self, update_src: UserModelWithRights, user_to_update: User
    ):
        if self._uservalidation is None or not self._uservalidation.account_validation:
            return False
        major_fields = [
            "name",
            "email",
            "organisation",
            "usercreationreason",
            "country",
        ]
        for f in major_fields:
            if getattr(update_src, f) != getattr(user_to_update, f):
                return True
        return False

    def _is_valid_user(self, mod_src: UserModelWithRights, user_id: int) -> None:
        # check if another user exists with the same new name or new email

        self._has_ident_user(
            mod_src.__dict__,
            False,
            user_id,
        )
        # check if it's a valid email - check should be done before exists but has to be compatible with data history
        if self._uservalidation is None:
            if mod_src.name == "":
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=[DETAIL_CANT_CHECK_VALIDITY],
                )
        elif not self._uservalidation.is_valid_email(mod_src.email):
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_INVALID_EMAIL],
            )

    def _keep_active(self, current_user: Optional[User] = None) -> bool:
        # check if required to change active state of user for revalidation
        if (
            self._uservalidation is None
            or self._uservalidation.account_validation == False
        ):
            return True
        is_admin = self._current_is_admin(current_user)
        if current_user is None:
            email = None
        else:
            email = current_user.email
        return self._uservalidation.keep_active(email, is_admin)

    def _get_active_user_by_email(self, email: str) -> Optional[User]:
        qry = (
            self.ro_session.query(User)
            .filter(User.email == email)
            .filter(User.status == UserStatus.active.value)
        )
        users = qry.all()
        if len(users) == 1:
            return users[0]
        return None

    def set_statusstate_user(
        self,
        user_id: UserIDT,
        status_name: Optional[str],
        current_user_id: Optional[UserIDT],
        no_bot: Optional[List[str]],
        token: Optional[str] = None,
        reason: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        if current_user_id is None:
            self._verify_captcha(no_bot)
            self._refresh_status(user_id, token=token, password=password)
        elif status_name is not None:
            status = UserStatus[status_name]
            if status is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=[DETAIL_INVALID_STATUS],
                )
            current_user: Optional[User] = self.ro_session.query(User).get(
                current_user_id
            )
            if current_user is None:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail=[NOT_AUTHORIZED]
                )

            self._set_user_status(
                current_user=current_user,
                user_id=user_id,
                status=status,
                comment=reason,
            )

    def _set_mail_status(
        self,
        update_src: UserModelWithRights,
        mail_status: bool,
        confirm: bool,
        user: Optional[User] = None,
        action: Optional[ActivationType] = None,
    ) -> UserModelWithRights:
        """
        modify user mail_status and mail_status_date
        """
        if user is not None and user.email == update_src.email:
            return update_src
        if action is None:
            action = ActivationType.create
        if self._uservalidation is not None and confirm and mail_status == False:
            if user is None:
                previous_email = None
            else:
                previous_email = user.email
            self._uservalidation.request_email_verification(
                update_src.email,
                self._get_assistance_email(),
                action=action,
                id=-1,
                previous_email=previous_email,
            )
            logger.info(
                "User email ['%s'] : requested verification '%s'"
                % (action, update_src.email)
            )
        update_src.mail_status = mail_status
        update_src.mail_status_date = DateTime.now_time()
        return update_src

    @staticmethod
    def _get_key_name(objdict: dict, value) -> Optional[str]:
        for k, v in objdict.items():
            if objdict[k] == v:
                return k
        return None

    # user activation after validation
    def _set_user_status(
        self,
        current_user: User,
        user_id: UserIDT,
        status: UserStatus,
        comment: Optional[str] = None,
    ) -> None:
        """
        modify user status, status_admin_comment and  status_date
        """
        if UserStatus(status) is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_INVALID_STATUS],
            )
        if self._current_is_admin(current_user, True):
            inactive_user: Optional[User] = self.session.query(User).get(user_id)
            if inactive_user is None:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=[NOT_AUTHORIZED]
                )
            if inactive_user.status != status.value:
                update_src = UserModelWithRights.from_orm(inactive_user)
                update_src.status = status.value
                update_src.status_date = DateTime.now_time()
                cols_to_upd = [User.status, User.status_date]
                if comment != None:
                    update_src.status_admin_comment = str(comment)
                    cols_to_upd.append(User.status_admin_comment)
                self._model_to_db(
                    inactive_user,
                    update_src,
                    cols_to_upd=cols_to_upd,
                    actions=None,
                )
                if self._uservalidation:
                    user_profile = UserModelProfile.from_orm(inactive_user)
                    if status == UserStatus.pending:
                        self._uservalidation.request_user_to_modify_profile(
                            user_profile,
                            self._get_assistance_email(),
                            reason=str(comment),
                            action=ActivationType.update,
                        )
                    else:
                        status_name = status.name
                        self._uservalidation.inform_user_status(
                            user_profile,
                            self._get_assistance_email(),
                            status_name=status_name,
                        )
        else:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=[NOT_AUTHORIZED])

    def _refresh_status(
        self, user_id: UserIDT, token: Optional[str], password: Optional[str]
    ) -> None:
        if not self._uservalidation:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        err = True
        if user_id != -1:
            user: Optional[User] = self.session.query(User).get(user_id)
            if user is None:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail=[NOT_AUTHORIZED]
                )
            now = DateTime.now_time()
            from datetime import timedelta

            if (
                self._uservalidation.account_validation == True
                and user.status == UserStatus.pending.value
            ):
                # reason can be empty when all validation dialog is made via email -
                # if requested : add an admin_comment field to the user account and send it to explain what needs to be modified in the reminder to the user.
                # resend emailmodification request  if it was sent more than 24h ago
                if not user.status_date or (user.status_date - now) < timedelta(
                    hours=PROFILE_TOKEN_AGE
                ):
                    update_src = UserModelWithRights.from_orm(user)
                    self._uservalidation.request_user_to_modify_profile(
                        UserModelProfile.from_orm(user),
                        self._get_assistance_email(),
                        reason=user.status_admin_comment,
                        action=ActivationType.update,
                    )
                    update_src.status_date = now
                    cols_to_upd = [User.status_date]
                    err = False

                elif user.mail_status == False:
                    if token:
                        id = self._uservalidation.get_id_from_token(token)
                        email = self._uservalidation.get_email_from_token(token)
                        if email == user.email and id == user.id:
                            with LoginService() as sce:
                                verified = sce.verify_and_update_password(
                                    password, user
                                )

                            if verified:
                                update_src = UserModelWithRights.from_orm(user)
                                update_src = self._set_mail_status(
                                    update_src, True, confirm=True
                                )
                                cols_to_upd = [User.mail_status, User.mail_status_date]
                                err = False

                    # resend email confirmation (of user email) if it was sent more than 1h ago
                    elif not user.mail_status_date or (
                        user.mail_status_date - now
                    ) < timedelta(hours=SHORT_TOKEN_AGE):
                        self._uservalidation.request_email_verification(
                            user.email,
                            self._get_assistance_email(),
                            action=ActivationType.update,
                            id=user.id,
                            previous_email=None,
                        )
                        update_src = UserModelWithRights.from_orm(user)
                        update_src.mail_status_date = now
                        cols_to_upd = [User.mail_status_date]
                        err = False
                if err:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=[NOT_AUTHORIZED],
                    )
                else:
                    self._model_to_db(
                        user,
                        update_src,
                        cols_to_upd=cols_to_upd,
                        actions=None,
                    )

    def _current_is_admin(
        self, current_user: Optional[User], is_main_admin: bool = False
    ) -> bool:
        """
        check if current_user can admin users
        """
        if current_user is not None:
            is_admin = current_user.has_role(
                Role.APP_ADMINISTRATOR
            ) or current_user.has_role(Role.USERS_ADMINISTRATOR)

            if not is_admin:
                return False
            if is_main_admin:
                if self._uservalidation is not None:
                    return current_user.has_role(Role.USERS_ADMINISTRATOR)
            return is_admin
        return False

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
                detail=[NOT_AUTHORIZED],
            )
        return verified

    def _verify_captcha(self, no_bot: Optional[List[str]]) -> None:
        recaptcha_secret, recaptcha_id = str(
            self.config.get_cnf("RECAPTCHASECRET") or ""
        ), str(self.config.get_cnf("RECAPTCHAID") or "")
        recaptcha = ReCAPTCHAClient(recaptcha_secret, recaptcha_id)
        recaptcha.verify_captcha(no_bot)

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
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
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
                status_code=HTTP_401_UNAUTHORIZED, detail=[NOT_AUTHORIZED]
            )
        id = -1
        if token:
            if resetreq.password is None or not UserValidation.is_strong_password(
                resetreq.password
            ):
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=[DETAIL_PASSWORD_STRENGTH_ERROR],
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
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=[NOT_FOUND]
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
                    else:
                        temp_rs.temp_password = hash_temp_password
                    self.session.commit()
                    user_profile = UserModelProfile.from_orm(user_ask_reset)
                    self._uservalidation.request_reset_password(
                        user_profile,
                        self._get_assistance_email(),
                        temp_password=temp_password,
                    )
                    err = False

            if err:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=[NOT_FOUND]
                )
        return id

    def _get_assistance_email(self) -> str:
        if self._assistance_email == "":
            users_admins = self.get_users_admins()
            if len(users_admins):
                u_lst = [u.email for u in users_admins if u.name.find(" - assistance")]
                if len(u_lst):
                    self._assistance_email = u_lst[0]
                else:
                    self._assistance_email = users_admins[0].email

        return self._assistance_email

    def _get_validation_emails(self) -> List[str]:
        if len(self._validation_emails) == 0:
            users_admins = self.get_users_admins()
            if len(users_admins) > 0:
                self._validation_emails = [u.email for u in users_admins]
            else:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=[DETAIL_NO_USERS_ADMIN],
                )
        return self._validation_emails
