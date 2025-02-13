# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import timedelta, timezone
from typing import Optional, List, Any, Tuple

from fastapi import HTTPException
from sqlalchemy import func

from API_models.crud import (
    UserModelWithRights,
    ProjectSummaryModel,
    ResetPasswordReq,
    UserActivateReq,
)
from BO.Classification import ClassifIDListT
from BO.Preferences import Preferences
from BO.Rights import RightsBO, NOT_AUTHORIZED, NOT_FOUND
from BO.User import (
    UserBO,
    UserIDT,
    UserIDListT,
    SHORT_TOKEN_AGE,
    PROFILE_TOKEN_AGE,
)
from DB.Project import ProjectIDT
from DB.User import User, Role, UserRole, TempPasswordReset, UserStatus, UserType, Guest, Person
from DB.Organization import Organization
from helpers import DateTime
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_VALIDATION_NOT_ACTIVE,
    DETAIL_INVALID_PARAMETER,
    DETAIL_PASSWORD_STRENGTH_ERROR,
    DETAIL_CANT_CHECK_VALIDITY,
    DETAIL_INVALID_EMAIL,
    DETAIL_INVALID_STATUS,
    DETAIL_NO_USERS_ADMIN,
    DETAIL_EMAIL_OWNED_BY_OTHER,
    DETAIL_NOTHING_DONE,
    DETAIL_NOT_FOUND,
)
from helpers.login import LoginService
from helpers.pydantic import BaseModel, Field
from providers.HomeCaptcha import HomeCaptcha
from ..helpers.Service import Service
from ..helpers.UserValidation import UserValidation, ActivationType

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
        self.verify_email = self.config.get_user_email_verification() == "on"
        self.account_validation = self.config.get_account_validation() == "on"
        if self.verify_email or self.account_validation:
            self._uservalidation = UserValidation()

    # Configuration keys TODO

    ADMIN_UPDATABLE_COLS = [
        User.email,
        User.password,
        User.name,
        User.status,
        User.organisation,
        User.country,
        User.orcid,
        User.usercreationreason,
    ]
    COMMON_UPDATABLE_COLS = [
        User.email,
        User.password,
        User.name,
        User.organisation,
        User.country,
        User.orcid,
        User.usercreationreason,
    ]

    EXCLUDE_KEYS = ["password", "last_used_projects", "can_do"]

    # check context to know if the email has to be verified

    def create_user(
        self,
        current_user_id: Optional[UserIDT],
        new_user: UserModelWithRights,
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> UserIDT:
        cols_to_upd:List=[]
        if new_user.id is None:
            new_user.id = -1
        if token is not None or current_user_id is None:
            # Unauthenticated user tries to create an account
            # Verify not a robot
            self._verify_captcha_throw(no_bot)
            # request email verification if  validation is on
            admin_user = None
            # check valid user
            if self.verify_email is True:
                if token:
                    if new_user.id > 0:
                       # update a profile with information requested - status to 0
                       user_id= self._modify_new_user(new_user, token)
                       return user_id
                    else:
                       new_user.mail_status = True
                       cols_to_upd.extend([User.mail_status])
                else:
                    #request email verification
                    self._is_valid_user_throw(new_user, new_user.id)
                    new_user, _ = self._set_mail_status(new_user, False)
                    return -1
        else:
            # Must be admin to create an account
            current_user: User = RightsBO.get_user_throw(
                self.ro_session, current_user_id
            )
            if not self._current_is_admin(current_user):
                raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])
            admin_user = current_user
        self._is_valid_user_throw(new_user, new_user.id)
        usr, new_user = self._new_user(new_user)
        cols_to_upd.extend(self.ADMIN_UPDATABLE_COLS)
        self._set_user_row(
            new_user,
            usr,
            action_type=ActivationType.create,
            cols_to_upd=cols_to_upd,
            current_user=admin_user,
        )
        return usr.id

    def _new_user(
        self, new_user: UserModelWithRights
    ) -> Tuple[User, UserModelWithRights]:
        guest: Optional[Guest] = (
            self.session.query(Guest.id)
            .filter(Guest.email.ilike(new_user.email))
            .scalar()
        )
        if guest is None:
            usr = User()
            #usr.name=new_user.name
            #usr.email=new_user.email
            #usr.organisation=new_user.organisation
            self.session.add(usr)
        else:
            usr = guest.to_user()
            new_user.id = usr.id
        usr.mail_status = False
        usr.status = 0

        return usr, new_user

    def _is_validation_active_throw(self) -> UserValidation:
        if not self._uservalidation:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        return self._uservalidation

    def _verify_token_throw(
        self, user_id: int, token: str, short: bool = True, email: Optional[str] = None
    ) -> int:
        self._uservalidation = self._is_validation_active_throw()
        token_email = self._uservalidation.get_email_from_token(token, short)
        token_user_id = self._uservalidation.get_id_from_token(token, short)
        if (
            token_email is None and email is not None and email != token_email
        ) or token_user_id != user_id:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_INVALID_PARAMETER],
            )
        return user_id

    @staticmethod
    def _verify_and_update_password_throw(new_password: str, usr: User):
        with LoginService() as sce:
            verified = sce.verify_and_update_password(new_password, usr)
        if not verified:
            raise HTTPException(
                status_code=403,
                detail=[NOT_AUTHORIZED],
            )

    def _modify_new_user(self, new_user: UserModelWithRights, token: str)->UserIDT:
        """
        user can modify major information before activation
        """
        self._uservalidation = self._is_validation_active_throw()
        user_id = self._verify_token_throw(new_user.id, token, short=False)
        # token verified,  user found and access verified by email and password - now check compatibility with other users in DB
        self._is_valid_user_throw(new_user, user_id)
        usr: Optional[User] = self.session.query(User).get(user_id)
        if usr is None:
            raise HTTPException(
                status_code=422,
                detail=[NOT_FOUND],
            )
        if usr.status != UserStatus.pending.value:
            detail = ["an active or valid or not checked profile cannot be replaced"]
            raise HTTPException(
                status_code=422,
                detail=detail,
            )
        else:
            self._verify_and_update_password_throw(new_user.password, usr)
        # update a profile with information requested by the main user admin - status to 0
        cols_to_upd = self.COMMON_UPDATABLE_COLS
        self._set_user_row(
                new_user,
                usr,
                action_type=ActivationType.update,
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
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        user_to_update: Optional[User] = self.session.query(User).get(user_id)
        if user_to_update is None:
            raise HTTPException(status_code=422, detail=[NOT_FOUND])
        self._is_valid_user_throw(update_src, user_to_update.id)
        if self._current_is_admin(current_user):
            if (current_user.id == user_to_update.id
                and update_src.status is None
            ):
                cols_to_upd = self.COMMON_UPDATABLE_COLS
            else:
                cols_to_upd = self.ADMIN_UPDATABLE_COLS
        elif (
            current_user.id == user_id
            and current_user.status == UserStatus.active.value
        ):
            cols_to_upd = self.COMMON_UPDATABLE_COLS
        else:
            raise HTTPException(
                status_code=403,
                detail=[NOT_AUTHORIZED],
            )
        self._set_user_row(
            update_src,
            user_to_update,
            action_type=ActivationType.update,
            cols_to_upd=cols_to_upd,
            current_user=current_user,
        )
        logger.info("User profile update %s :  '%s'" % (update_src.email, user_id))

    def set_status_state_user(
        self,
        user_id: UserIDT,
        status_name: Optional[str],
        current_user_id: Optional[UserIDT],
        no_bot: Optional[List[str]],
        activate_req: Optional[UserActivateReq] = None,
    ) -> None:
        """
        Either change the status of the user if current_user is not None and is admin or confirm mail_status and start validation process if account_validation is True.
        """
        if current_user_id is None:
            self._verify_captcha_throw(no_bot)
            if activate_req is not None and user_id != -1:
                self._refresh_any_status(
                    user_id, token=activate_req.token, password=activate_req.password
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail=[DETAIL_INVALID_PARAMETER],
                )
        elif status_name is not None:
            status = UserStatus[status_name]
            if status is None:
                raise HTTPException(
                    status_code=422,
                    detail=[DETAIL_INVALID_STATUS],
                )
            # current_user: Optional[User] = self.ro_session.query(User).get(current_user_id )
            current_user: User = RightsBO.get_user_throw(
                self.ro_session, current_user_id
            )
            if activate_req is not None:
                comment = activate_req.reason
            else:
                comment = None
            self._set_user_status(
                current_user=current_user,
                user_id=user_id,
                status=UserStatus(status),
                comment=comment,
            )

    def search_by_id(
        self, user_id: UserIDT
    ) -> Optional[User]:
        # TODO: Not consistent with others e.g. project.query()
        ret = self.ro_session.query(User).get(user_id)
        return ret

    def get_full_by_id(
        self, current_user_id: UserIDT, user_id: UserIDT
    ) -> UserModelWithRights:
        _: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        db_usr = self.ro_session.query(User).get(user_id)
        if db_usr is None:
            raise HTTPException(status_code=404, detail=DETAIL_NOT_FOUND)
        else:
            ret = self._get_full_user(db_usr)
        ret.password = "?"
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
    @staticmethod
    def _get_user_with_rights(db_usr: User) -> UserModelWithRights:
        ret = UserModelWithRights.from_orm(db_usr)
        ret.can_do = [act.value for act in RightsBO.get_allowed_actions(db_usr)]
        ret.password = "?"
        return ret
    @staticmethod
    def _get_user_profile(db_usr: User) -> UserModelWithRights:
        ret = UserModelWithRights.from_orm(db_usr)
        ret.password = "?"
        return ret

    def search(self, current_user_id: UserIDT, by_name: Optional[str]) -> List[User]:
        _: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
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

    def get_admin_users(self) -> List[User]:
        """
        List persons with the APP_ADMINISTRATOR role.
        """
        return self._get_users_with_role(Role.APP_ADMINISTRATOR)


    def list(
        self,
        current_user_id: UserIDT,
        user_ids: UserIDListT,
        fields: str = "*summary",
    ) -> List[UserModelWithRights]:
        """
        List all users, or some of them by their ids, if requester is admin.
        """
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        ret = []
        if self._current_is_admin(current_user):
            # for faster display in test
            # get_user_details = self._get_full_user
            if fields == "*summary":
                get_user_details = self._get_user_with_rights
            else:
                get_user_details = self._get_user_profile
            qry = self.ro_session.query(User)
            if len(user_ids) > 0:
                qry = qry.filter(User.id.in_(user_ids))
            for db_usr in qry:
                ret.append(get_user_details(db_usr))
        ret = sorted(ret, key=lambda d: d.id, reverse=True)
        return ret

    def get_preferences_per_project(
        self, user_id: UserIDT, project_id: ProjectIDT, key: str
    ) -> Any:
        """
        Get a preference, for given project and user. Keys are not standardized (for now).
        """
        return UserBO.get_preferences_per_project(
            self.ro_session, user_id, project_id, key
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
        cols_to_upd: List,
        actions: Optional[List] = None,
    ) -> None:
        """
        Transfer model values into the DB record.
        """
        self._validate_user_throw(
            update_src, user_to_update, (User.password in cols_to_upd)
        )
        # change status_date and mail_status_date if values were modified
        now = DateTime.now_time()
        if update_src.status != user_to_update.status:
            update_src.status_date = now
            cols_to_upd.append(User.status_date)
        if update_src.mail_status != user_to_update.mail_status:
            update_src.mail_status_date = now
            cols_to_upd.append(User.mail_status_date)
        if len(cols_to_upd) == 0:
            return None
        errors: List[str] = UserBO.check_fields(update_src.__dict__, UserBO.to_check)
        if len(errors) > 0:
            raise HTTPException(
                status_code=422,
                detail=errors,
            )
        for col in cols_to_upd:
            if update_src.id == -1 and col.name == User.usercreationdate.name:
                value = DateTime.now_time()
            elif col==User.password:
                value = getattr(update_src, User.password.name)
                if value not in ("", None):
                    with LoginService() as sce:
                        value = sce.hash_password(value)
            else:
                value = getattr(update_src,col.name)
            if update_src.id == -1 or value is not None:
                setattr(user_to_update, col.name, value)
        if actions is not None:
            # Set roles so that requested actions will be possible
            all_roles = {a_role.name: a_role for a_role in self.session.query(Role)}
            RightsBO.set_allowed_actions(user_to_update, actions, all_roles)
        self.session.commit()

    def search_organizations(self, name: str) -> List[str]:
        """
        Return the already-used org names with given pattern.
        """
        qry = self.ro_session.query(Organization.name)
        qry = qry.filter(Organization.name.ilike(name))
        return [r for r, in qry if r is not None]

    def _has_ident_user_throw(
        self, user_data: dict, valid: bool, _id: int = -1
    ) -> None:
        """
        Exception if the mail exists and valid is False or the mail does not exists and valid is True
        """
        detail = []
        if "email" not in user_data.keys():
            detail = [DETAIL_CANT_CHECK_VALIDITY]
        else:
            is_other: Optional[Person] = UserBO.has_ident_person(
                self.ro_session, user_data, _id
            )
            if valid:
                #if guest found it is like user not found
                if is_other is not None and is_other.type!=UserType.user:
                    detail = [NOT_FOUND]
            elif is_other is not None:
                if is_other.type==UserType.user:
                    detail = [DETAIL_EMAIL_OWNED_BY_OTHER]
                else:
                    # this case can happen  when the same person is registered as guest and user with different email
                    # TODO case to be evaluated
                    detail = [DETAIL_EMAIL_OWNED_BY_OTHER]

        if len(detail):
            raise HTTPException(
                status_code=422,
                detail=detail,
            )

    def _mail_status_on(
        self, update_src: UserModelWithRights, user_to_update: User
    ) -> bool:
        return (
            self.verify_email == False
            or update_src.id == -1
            or (update_src.email.lower() == user_to_update.email.lower() and user_to_update.mail_status )
        )

    def _ask_activate_on(
        self,
        update_src: UserModelWithRights,
        user_to_update: User,
        cols_to_upd: List,
        mail_status: bool,
    ) -> bool:
        if not self.account_validation:
            return False
        # user confirmed email
        confirmed = self.verify_email is not True or mail_status is True
        # email confirmation if email_verification is on
        just_confirmed = (
            (update_src.id == -1 or (user_to_update.status == UserStatus.inactive.value))
            and confirmed
        ) and User.mail_status in cols_to_upd
        # TODO add "and confirmed"  for current_status_on when batch mail to modifiy email has been sent
        current_status_on = user_to_update.status in [
            UserStatus.active.value,
            UserStatus.pending.value,
        ]
        # data modified have to be verified
        major_update = (
            User.status in cols_to_upd
            and update_src.status == UserStatus.inactive.value
        ) and user_to_update.email == update_src.email

        return (major_update and current_status_on) or just_confirmed

    def _validate_user_throw(
        self, update_src: UserModelWithRights, user_to_update: User, add_condition=True
    ) -> None:
        verify_password = (
            add_condition
            and self._uservalidation is not None
            and (update_src.password != user_to_update.password)
        )
        UserBO.validate_usr(update_src, verify_password)

    def _set_user_row(
        self,
        update_src: UserModelWithRights,
        user_to_update: User,
        action_type: ActivationType,
        cols_to_upd: List,
        current_user: Optional[User],
    ):
        """
        common to add or update a user
        """
        inform_about_status = False
        actions = None
        is_admin = current_user is not None and self._current_is_admin(current_user)
        # check if the account needs validation or re-validation
        ask_activate = None
        if is_admin:
            # only update actions from admin - not from profile
            if current_user is not None and current_user.id != user_to_update.id:
                actions = update_src.can_do
                inform_about_status = (
                    update_src.status != user_to_update.status and update_src.id != -1
                )
            # only modify the comment with the status  -
            if update_src.status_admin_comment != user_to_update.status_admin_comment:
                cols_to_upd.append(User.status_admin_comment)
            ask_activate = False

        elif self._is_major_data_change(update_src, user_to_update):
            # validate and throw error if needed
            self._validate_user_throw(update_src, user_to_update)
            # condition for mail_status==True
            mail_status:bool = self._mail_status_on(update_src, user_to_update)
            # email is checked if the user is new
            if mail_status != user_to_update.mail_status:
                update_src, add_cols = self._set_mail_status(
                    update_src,
                    mail_status,
                    user=user_to_update,
                    action=action_type,
                )
                cols_to_upd.extend(add_cols)
            else:
                # ordinary user cannot modify major data if external validation is on
                keep_active = self._keep_active(current_user)
                update_src.status = int(keep_active and mail_status is True)
                cols_to_upd.append(User.status)
            ask_activate = self._ask_activate_on(
                update_src, user_to_update, cols_to_upd, mail_status
            )
        if ask_activate is None and len(cols_to_upd) == 0:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_NOTHING_DONE],
            )
        self._model_to_db(
            user_to_update,
            update_src,
            cols_to_upd=cols_to_upd,
            actions=actions,
        )
        logger.info("User %s :  '%s'" % (action_type.name, user_to_update.email))
        # condition send validation request email only if not is_admin and account_validation is "on"

        self._conditional_validation(
            user_to_update,
            ask_activate,
            inform_about_status,
            action_type,
        )

    def _get_assistance_email(self) -> str:
        if self._assistance_email == "":
            from_config = self.config.get_app_manager()
            if from_config[1] is not None:
                self._assistance_email = str(from_config[1] or None)
            if self._assistance_email is None:
                users_admins = self.get_users_admins()
                if len(users_admins):
                    u_lst = [
                        u.email for u in users_admins if u.name.find(" - assistance")
                    ]
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
                    status_code=422,
                    detail=[DETAIL_NO_USERS_ADMIN],
                )
        return self._validation_emails

    def _conditional_validation(
        self,
        user_to_update: User,
        ask_activate: Optional[bool],
        inform_about_status: bool,
        action_type: ActivationType,
    ) -> None:
        # check if we have to send activation request email
        if self._uservalidation:
            if ask_activate:
                validation_emails = self._get_validation_emails()
                self._uservalidation.request_activate_user(
                    UserModelWithRights.from_orm(user_to_update),
                    validation_emails=validation_emails,
                    action=action_type.value,
                )
            elif inform_about_status:
                if user_to_update.status is None:
                    raise HTTPException(
                        status_code=422,
                        detail=[DETAIL_INVALID_STATUS],
                    )
                status_name = UserStatus(user_to_update.status).name
                assistance_email = self._get_assistance_email()
                self._uservalidation.inform_user_status(
                    UserModelWithRights.from_orm(user_to_update),
                    assistance_email,
                    status_name=status_name,
                )
    @staticmethod
    def _is_major_data_change(
        update_src: UserModelWithRights,
        user_to_update: User,
    ):
        major_fields = [
            "name",
            "email",
            "organisation",
            "usercreationreason",
            "country",
            # "orcid",
        ]
        for f in major_fields:
            if getattr(update_src, f) != getattr(user_to_update, f):
                return True
        return False

    def _is_valid_user_throw(self, mod_src: UserModelWithRights, user_id: int) -> None:
        # check if another user exists with the same new name or new email
        self._has_ident_user_throw(
            mod_src.__dict__,
            False,
            user_id,
        )
        # check if it's a valid email - check should be done before exists but has to be compatible with data history
        if self._uservalidation is None:
            if mod_src.name == "":
                raise HTTPException(
                    status_code=422,
                    detail=[DETAIL_CANT_CHECK_VALIDITY],
                )
        elif not self._uservalidation.is_valid_email(mod_src.email):
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_INVALID_EMAIL],
            )

    def _keep_active(self, current_user: Optional[User] = None) -> bool:
        # check if required to change active state of user for revalidation
        if not self.account_validation:
            return True
        if current_user is None:
            return not self.account_validation
        else:
            is_admin = self._current_is_admin(current_user)
            return is_admin or not self.account_validation

    def _get_active_user_by_email(self, email: str) -> Optional[User]:
        qry = (
            self.ro_session.query(User)
            .filter(func.lower(User.email) == func.lower(email))
            .filter(User.status == UserStatus.active.value)
        )
        users = qry.all()
        if len(users) == 1:
            return users[0]
        return None

    def _verify_captcha_throw(self, no_bot: Optional[List[str]]) -> None:
        recaptcha = HomeCaptcha(str(self.config.get_mailservice_secret_key() or ""))
        # verify_captcha throws exception
        recaptcha.verify_captcha(no_bot)

    def _set_mail_status(
        self,
        update_src: UserModelWithRights,
        mail_status: bool,
        user: Optional[User] = None,
        action: Optional[ActivationType] = None,
    ) -> Tuple[UserModelWithRights, List[Any]]:
        """
        modify user mail_status
        """
        status_cols: List[Any] = []
        has_to_refresh = action == ActivationType.refresh
        if (
            has_to_refresh == False
            and user is not None
            and str(user.email or "").lower() == str(update_src.email or "").lower()
            and mail_status == update_src.mail_status
        ) or self.verify_email is not True:
            return update_src, status_cols
        if action is None:
            action = ActivationType.create
        if (
            mail_status == False or has_to_refresh == True
        ) and self._uservalidation is not None:
            if user is None:
                previous_email = None
            else:
                previous_email = user.email
            assistance_email = self._get_assistance_email()
            self._uservalidation.request_email_verification(
                update_src.email,
                assistance_email,
                action=action,
                id=update_src.id,
                previous_email=previous_email,
            )
            logger.info("User email [%s] '%s' : requested verification '%s'" % (str(update_src.id), action, update_src.email))
        if has_to_refresh:
            update_src.mail_status_date = DateTime.now_time()
            status_cols = [User.mail_status_date]
        else:
            update_src.mail_status = mail_status
            status_cols.append(User.mail_status)
            keep_active = self._keep_active()
            update_src.status = int(keep_active and mail_status == True)
            if user is None or update_src.status != user.status:
                status_cols.append(User.status)
        return update_src, status_cols

    @staticmethod
    # https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier
    # TODO use to verify orcid
    def generate_check_digit(base_digits: str):
        total = 0
        for i in range(0, len(base_digits)):
            digit = int(base_digits[i])
            total = (total + digit) * 2
        remainder = total % 11
        result = (12 - remainder) % 11
        if result == 10:
            return "X"
        return str(result)

    # user activation after validation
    def _set_user_status(
        self,
        current_user: User,
        user_id: UserIDT,
        status: UserStatus,
        comment: Optional[str] = None,
    ) -> None:
        """
        admin modify user status, status_admin_comment and  status_date
        """
        if status is None:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_INVALID_STATUS],
            )

        if not self._current_is_admin(current_user, True):
            raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])
        inactive_user: Optional[User] = self.session.query(User).get(user_id)
        if inactive_user is None:
            raise HTTPException(status_code=422, detail=[NOT_FOUND])
        cols_to_upd = []
        update_src = UserModelWithRights.from_orm(inactive_user)
        if inactive_user.status != status.value:
            update_src.status = status.value
            update_src.status_date = DateTime.now_time()
            cols_to_upd = [User.status, User.status_date]
        if comment != inactive_user.status_admin_comment:
            update_src.status_admin_comment = str(comment or "")
            cols_to_upd.append(User.status_admin_comment)
        if len(cols_to_upd):
            self._model_to_db(
                inactive_user,
                update_src,
                cols_to_upd=cols_to_upd,
            )
        if self._uservalidation:
            user_profile = UserModelWithRights.from_orm(inactive_user)
            assistance_email = self._get_assistance_email()
            if self.account_validation == True and status == UserStatus.pending:
                # reason can be empty when all validation dialog is made via email -
                # if requested : add an admin_comment field to the user account and send it to explain what needs to be modified in the reminder to the user. ticket number can be included
                self._uservalidation.request_user_to_modify_profile(
                    user_profile,
                    assistance_email,
                    reason=str(comment or ""),
                    action=ActivationType.update,
                )
            else:
                status_name = status.name
                self._uservalidation.inform_user_status(
                    user_profile,
                    assistance_email,
                    status_name=status_name,
                )

    def _refresh_mail_status_throw(
        self,
        user: User,
        update_src: UserModelWithRights,
        token: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Tuple[UserModelWithRights, List]:
        if (
            self.verify_email is not True
            or user.mail_status is True
            or self._uservalidation is None
        ):
            return update_src, []
        mail_status : bool = user.mail_status
        if token is not None:
            email = self._uservalidation.get_email_from_token(token)
            user_id = self._uservalidation.get_id_from_token(token)
            mail_status = True
            if (
                str(email or "").lower() == str(user.email or "").lower()
                and user_id == user.id
            ):
                self._verify_and_update_password_throw(str(password), user)
            if user.id == -1:
                action = ActivationType.create
            else:
                # update status
                action = ActivationType.update
        else:
            action = ActivationType.refresh
        update_src, add_cols = self._set_mail_status(
            update_src, mail_status, user=user, action=action
        )
        return update_src, add_cols

    def _refresh_any_status(
        self,
        user_id: UserIDT,
        token: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self._uservalidation = self._is_validation_active_throw()
        user: Optional[User] = self.session.query(User).get(user_id)
        if user is None or user.status == UserStatus.blocked.value:
            # no action if wrong id or user is blocked
            raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])
        cols_to_upd = []
        now = DateTime.now_time()
        update_src = UserModelWithRights.from_orm(user)
        # delay between emails is too short
        token_age = [SHORT_TOKEN_AGE, PROFILE_TOKEN_AGE]
        if user.status_date is not None:
            datenow = now - user.status_date.replace(tzinfo=timezone.utc)
        else:
            datenow = now - (now - timedelta(days=2))
        if token is None and (
            user.status == UserStatus.active.value
            or (
                user.status_date
                and datenow
                < timedelta(
                    hours=token_age[
                        int(user.mail_status is not None and user.mail_status is True)
                    ]
                )
            )
        ):
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_NOTHING_DONE],
            )
        if self.verify_email == True and user.mail_status != True and token:
            update_src, add_cols = self._refresh_mail_status_throw(
                user, update_src, token, password
            )
            cols_to_upd.extend(add_cols)
        elif self.account_validation == True and user.mail_status == True:
            # mail_status is True and account_validation is True
            if user.status == UserStatus.pending.value:
                self._uservalidation.request_user_to_modify_profile(
                    UserModelWithRights.from_orm(user),
                    self._get_assistance_email(),
                    reason=user.status_admin_comment,
                    action=ActivationType.update,
                )
                update_src.status_date = now
                cols_to_upd.append(User.status_date)
            elif token and user.status == UserStatus.inactive.value:
                # send activation request to users administrators
                self._conditional_validation(
                    user,
                    ask_activate=True,
                    inform_about_status=False,
                    action_type=ActivationType.update,
                )
        else:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_NOTHING_DONE],
            )
        if len(cols_to_upd):
            self._model_to_db(
                user,
                update_src,
                cols_to_upd=cols_to_upd,
            )

    def _current_is_admin(
        self, current_user: User, is_main_admin: bool = False
    ) -> bool:
        """
        check if current_user can admin users
        """
        is_admin = (
            current_user.status == UserStatus.active.value
            and current_user.has_role(Role.APP_ADMINISTRATOR)
            or current_user.has_role(Role.USERS_ADMINISTRATOR)
        )
        if is_admin and is_main_admin and self._uservalidation is not None:
            return current_user.has_role(Role.USERS_ADMINISTRATOR)
        return is_admin

    @staticmethod
    def _verify_temp_password(
        temp_password: str, temp: Optional[TempPasswordReset]
    ) -> bool:
        """
        Returns ``True`` if the temporary password is valid for the specified user id.
        :param temp_password: A plaintext password to verify
        """
        if temp is None:
            return False
        with LoginService() as sce:
            if sce.use_double_hash(temp.temp_password):
                verified = sce.pwd_context.verify(
                    sce.get_hmac(temp_password), temp.temp_password
                )
            else:
                # Try with plaintext password.
                verified = sce.pwd_context.verify(temp_password, temp.temp_password)
        if not verified:
            raise HTTPException(
                status_code=401,
                detail=[NOT_AUTHORIZED],
            )
        return verified

    def reset_password(
        self,
        current_user_id: Optional[UserIDT],
        reset_req: ResetPasswordReq,
        no_bot: Optional[List[str]],
        token: Optional[str],
    ) -> UserIDT:
        """
        Reset a user password by creating a token and temporary password then sending the information and update the modified password.
        TODO : move to _uservalidation when Users model and "crud ops" are normalized
        """
        # active only when validation is on
        self._uservalidation = self._is_validation_active_throw()
        if current_user_id is not None:
            # reset only if not connected
            raise HTTPException(status_code=422, detail=[DETAIL_NOTHING_DONE])
        # Unauthenticated user asks to reset his password
        # Verify not a robot
        self._verify_captcha_throw(no_bot)
        if token:
            user_id = self._reset_password_with_token_throw(reset_req, token)
        else:
            # verify if the email exists  in the db
            self._has_ident_user_throw(dict({"email": reset_req.email}), True)
            # store a temporary unique password in the db for the user_id
            user_id = self._set_temporary_password_throw(reset_req)

        return user_id

    def _reset_password_with_token_throw(
        self, reset_req: ResetPasswordReq, token: str
    ) -> UserIDT:
        self._uservalidation = self._is_validation_active_throw()
        if reset_req.password is None or not UserBO.is_strong_password(
            reset_req.password
        ):
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_PASSWORD_STRENGTH_ERROR],
            )

        self._uservalidation.get_email_from_token(token)
        temp_password = self._uservalidation.get_reset_from_token(token)
        user_id = self._uservalidation.get_id_from_token(token)
        err = True
        if temp_password is not None and user_id != -1:
            user_to_reset: Optional[User] = self.session.query(User).get(user_id)
            if user_to_reset is not None:
                # find temporary password
                temp = self.ro_session.query(TempPasswordReset).get(user_id)
                if temp is not None:
                    verified = self._verify_temp_password(str(temp_password), temp)
                    if verified:
                        update_src = UserModelWithRights.from_orm(user_to_reset)
                        update_src.password = reset_req.password
                        self._model_to_db(
                            user_to_reset,
                            update_src,
                            [User.password],
                        )
                        # remove temp_user_reset row
                        temp_pw: Optional[TempPasswordReset] = self.session.query(
                            TempPasswordReset
                        ).get(user_to_reset.id)
                        self.session.delete(temp_pw)
                        self.session.commit()
                        err = False
        if err:
            raise HTTPException(status_code=422, detail=[NOT_FOUND])
        return user_id

    def _set_temporary_password_throw(self, reset_req: ResetPasswordReq) -> UserIDT:
        # store a temporary unique password in the db for the user_id
        self._uservalidation = self._is_validation_active_throw()
        err = True
        email = str(reset_req.email or "")
        user_id = -1
        if email != "":
            user_ask_reset: Optional[User] = self._get_active_user_by_email(email)
            if user_ask_reset is not None:
                import uuid

                temp_password = uuid.uuid4().hex
                with LoginService() as sce:
                    hash_temp_password = sce.hash_password(temp_password)
                    temp_rs: Optional[TempPasswordReset] = self.session.query(
                        TempPasswordReset
                    ).get(user_ask_reset.id)
                if temp_rs is None:
                    temp_rs=TempPasswordReset()
                    temp_rs.user_id=user_ask_reset.id
                    temp_rs.temp_password=hash_temp_password
                    self.session.add(temp_rs)
                else:
                    temp_rs.temp_password = hash_temp_password
                    user_id = user_ask_reset.id
                self.session.commit()
                user_profile = UserModelWithRights.from_orm(user_ask_reset)
                assistance_email = self._get_assistance_email()
                self._uservalidation.request_reset_password(
                    user_profile,
                    assistance_email,
                    temp_password=temp_password,
                )
                err = False
        if err:
            raise HTTPException(status_code=422, detail=[NOT_FOUND])
        return user_id
