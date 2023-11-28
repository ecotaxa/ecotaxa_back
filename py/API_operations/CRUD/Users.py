# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, List, Any, Tuple
from sqlalchemy import func
from API_models.crud import (
    UserModelWithRights,
    ProjectSummaryModel,
    UserModelProfile,
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
from DB.User import User, Role, UserRole, TempPasswordReset, UserStatus
from helpers.DynamicLogs import get_logger
from helpers.pydantic import BaseModel, Field
from helpers.login import LoginService
from providers.HomeCaptcha import HomeCaptcha
from ..helpers.Service import Service
from fastapi import HTTPException
from ..helpers.UserValidation import UserValidation, ActivationType
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
    DETAIL_NOTHING_DONE,
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
            self._verify_captcha_thow(no_bot)
            # No right at all
            actions = None
            # request email verification if  validation is on
            if self.verify_email == True:
                if token:
                    if new_user.id is not None and new_user.id > 0:
                        return self._modify_new_user(new_user, token)
                else:
                    # check valid user
                    self._is_valid_user_throw(new_user, -1)
                    new_user, addcols = self._set_mail_status(new_user, False)
                    return -1
        else:
            # Must be admin to create an account
            # current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
            current_user: User = RightsBO.get_user_throw(
                self.ro_session, current_user_id
            )
            if not self._current_is_admin(current_user):
                raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])
        if new_user.id is None:
            new_user.id = -1
        self._is_valid_user_throw(new_user, -1)
        usr = User()
        self.session.add(usr)
        if current_user_id is None:
            admin_user = None
        else:
            admin_user = current_user
        self._set_user_row(
            new_user,
            usr,
            actiontype=ActivationType.create,
            cols_to_upd=cols_to_upd,
            current_user=admin_user,
        )
        return usr.id

    def _verify_token_throw(
        self, new_user: UserModelWithRights, token: str, short: bool = True
    ) -> int:
        if not self._uservalidation:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        email = self._uservalidation.get_email_from_token(token, short)
        user_id = self._uservalidation.get_id_from_token(token, short)
        if email is None or user_id != new_user.id:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_INVALID_PARAMETER],
            )
        return new_user.id

    def _modify_new_user(self, new_user: UserModelWithRights, token: str) -> UserIDT:
        """
        user can modify major information before activation
        """
        if not self._uservalidation:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        if not token:
            raise HTTPException(
                status_code=401,
                detail=[NOT_AUTHORIZED],
            )
        user_id = self._verify_token_throw(new_user, token, short=False)
        detail = None

        verified = False
        usr: Optional[User] = self.session.query(User).get(user_id)

        if usr is None:
            raise HTTPException(
                status_code=422,
                detail=[NOT_FOUND],
            )

        if usr.status != UserStatus.pending.value:
            detail = ["an active or valid or not checked profile cannot be replaced"]
        else:
            with LoginService() as sce:
                verified = sce.verify_and_update_password(new_user.password, usr)
        if not verified:
            raise HTTPException(
                status_code=403,
                detail=[NOT_AUTHORIZED],
            )

        if detail:
            raise HTTPException(
                status_code=422,
                detail=detail,
            )
        # token verified,  user found and access verified by email and password - now check compatibility with other users in DB
        self._is_valid_user_throw(new_user, user_id)
        # update a profile with informations requested by the main user admin - status to 0
        cols_to_upd = self.COMMON_UPDATABLE_COLS
        self._set_user_row(
            new_user,
            usr,
            actiontype=ActivationType.update,
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
        # current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        user_to_update: Optional[User] = self.session.query(User).get(user_id)
        if user_to_update is None:
            raise HTTPException(status_code=422, detail=[NOT_FOUND])
        self._is_valid_user_throw(update_src, user_to_update.id)

        if self._current_is_admin(current_user):
            if (
                user_to_update is not None
                and current_user.id == user_to_update.id
                and update_src.status == None
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
            actiontype=ActivationType.update,
            cols_to_upd=cols_to_upd,
            current_user=current_user,
        )
        logger.info("User profile update %s :  '%s'" % (update_src.email, user_id))

    def set_statusstate_user(
        self,
        user_id: UserIDT,
        status_name: Optional[str],
        current_user_id: Optional[UserIDT],
        no_bot: Optional[List[str]],
        activatereq: Optional[UserActivateReq] = None,
    ) -> None:
        """
        Either change the status of the user if current_user is not None and is admin or confirm mail_status and start validation process if account_validation is True.
        """
        if current_user_id is None:
            self._verify_captcha_thow(no_bot)
            if activatereq is not None:

                self._refresh_any_status(
                    user_id, token=activatereq.token, password=activatereq.password
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
            if activatereq is not None:
                comment = activatereq.reason
            else:
                comment = None
            self._set_user_status(
                current_user=current_user,
                user_id=user_id,
                status=status,
                comment=comment,
            )

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
            raise HTTPException(status_code=404, detail="Item not found")
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
        # current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
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
        verify_password = (
            self._uservalidation is not None
            and User.password in cols_to_upd
            and (update_src.password != user_to_update.password)
        )

        UserBO.validate_usr(self.session, update_src, verify_password)
        # change status_date and mail_status_date if values were modified
        now = DateTime.now_time()
        if update_src.status != user_to_update.status:
            update_src.status_date = now
            cols_to_upd.append(User.status_date)
        if update_src.mail_status != user_to_update.mail_status:
            update_src.mail_status_date = now
            cols_to_upd.append(User.mail_status_date)
        # Do the in-memory update
        cols_to_upd = set(cols_to_upd)
        for a_col in cols_to_upd:
            col_name = a_col.name
            new_val = getattr(update_src, col_name)
            if update_src.id != -1 and new_val is None:
                continue
            if a_col == User.password:
                if new_val in ("", None):
                    # By policy, don't clear passwords
                    continue
                else:
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
        Exception if the mail exists and valid is False or the mail does not exists and valid is True
        """
        qry = self.ro_session.query(User)
        if "id" in userdata.keys() and id != userdata["id"]:
            id == userdata["id"]
        if id != -1:
            qry = qry.filter(User.id != id)
        is_other = False
        detail = []
        if "email" not in userdata.keys():
            detail = [DETAIL_CANT_CHECK_VALIDITY]
        else:
            is_other = (
                qry.filter(
                    func.lower(User.email) == func.lower(str(userdata["email"] or ""))
                ).scalar()
                != None
            )
            if is_other and not valid:
                detail = [DETAIL_EMAIL_OWNED_BY_OTHER]
            elif is_other != valid:
                detail = [NOT_FOUND]
        if len(detail):
            raise HTTPException(
                status_code=422,
                detail=detail,
            )

    def _set_user_row(
        self,
        update_src: UserModelWithRights,
        user_to_update: User,
        actiontype: ActivationType,
        cols_to_upd: List,
        current_user: Optional[User],
    ):
        """
        common to add or update a user
        """
        ask_activate = False
        inform_about_status = None
        is_admin = current_user is not None and self._current_is_admin(current_user)

        # check if must send confirmation email before any update
        if (
            str(update_src.email or "").lower()
            != str(user_to_update.email or "").lower()
        ):
            # validate before sending mail status
            verify_password = self._uservalidation is not None and (
                update_src.password != user_to_update.password
            )
            UserBO.validate_usr(self.session, update_src, verify_password)
            if self.verify_email == True and not is_admin:
                mail_status = update_src.id == -1
                update_src, addcols = self._set_mail_status(
                    update_src,
                    mail_status,
                    user=user_to_update,
                    action=actiontype,
                )
                if len(addcols):
                    cols_to_upd.extend(addcols)
                    # desactivate when
                    update_src.status = int(
                        self._keep_active(current_user) and mail_status == True
                    )
                    cols_to_upd.append(User.status)
                    inform_about_status = False
        # check if the account needs validation or re-validation
        elif is_admin:
            if (
                (update_src.status != user_to_update.status)
                and update_src.id != -1
                and User.status in cols_to_upd
            ):
                inform_about_status = True
                # only modify the comment with the status  -
                if (
                    update_src.status_admin_comment
                    != user_to_update.status_admin_comment
                ):
                    cols_to_upd.append(User.status_admin_comment)
        elif self._is_major_data_change(update_src, user_to_update):
            if not self._keep_active(current_user):
                update_src.status = UserStatus.inactive.value
                cols_to_upd.append(User.status)
            else:
                # ordinary user cannot change his status
                update_src.status = user_to_update.status
        if (
            is_admin == False
            and update_src.status != user_to_update.status
            and (
                update_src.status == UserStatus.inactive.value
                and self.account_validation == True
            )
        ):
            ask_activate = True
        # only update actions from admin - not from profile
        if (
            current_user is not None
            and is_admin
            and (current_user.id != user_to_update.id or len(update_src.can_do) > 0)
        ):
            actions = update_src.can_do
        else:
            actions = None
        self._model_to_db(
            user_to_update,
            update_src,
            cols_to_upd=cols_to_upd,
            actions=actions,
        )
        logger.info("User %s :  '%s'" % (actiontype.name, user_to_update.email))
        if self._uservalidation:
            if ask_activate:
                self._uservalidation.request_activate_user(
                    UserModelProfile.from_orm(user_to_update),
                    validation_emails=self._get_validation_emails(),
                    action=actiontype.value,
                )
            elif is_admin and inform_about_status == True:
                if user_to_update.status is None:
                    raise HTTPException(
                        status_code=422,
                        detail=[DETAIL_INVALID_STATUS],
                    )
                status_name = UserStatus(user_to_update.status).name
                self._uservalidation.inform_user_status(
                    UserModelProfile.from_orm(user_to_update),
                    self._get_assistance_email(),
                    status_name=status_name,
                )

    def _is_major_data_change(
        self,
        update_src: UserModelWithRights,
        user_to_update: User,
    ):
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

    def _is_valid_user_throw(self, mod_src: UserModelWithRights, user_id: int) -> None:
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
        if self.account_validation != True:
            return True
        if current_user is None:
            return not self.account_validation
        else:
            is_admin = self._current_is_admin(current_user)
            return is_admin or self.account_validation != True

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

    def _verify_captcha_thow(self, no_bot: Optional[List[str]]) -> None:
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
        modify user mail_status and mail_status_date
        """
        status_cols: List[Any] = []
        if (
            user is not None
            and str(user.email or "").lower() == str(update_src.email or "").lower()
        ):
            return update_src, status_cols
        if action is None:
            action = ActivationType.create
        if self.verify_email != True:
            return update_src, status_cols
        if mail_status == False:
            if self._uservalidation is not None:
                if user is None:
                    previous_email = None
                else:
                    previous_email = user.email

                self._uservalidation.request_email_verification(
                    update_src.email,
                    self._get_assistance_email(),
                    action=action,
                    id=update_src.id,
                    previous_email=previous_email,
                )
                logger.info(
                    "User email [%s] '%s' : requested verification '%s'"
                    % (str(update_src.id), action, update_src.email)
                )
        update_src.mail_status = mail_status
        status_cols.append(User.mail_status)
        return update_src, status_cols

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
                status_code=422,
                detail=[DETAIL_INVALID_STATUS],
            )
        if self._current_is_admin(current_user, True):
            inactive_user: Optional[User] = self.session.query(User).get(user_id)
            if inactive_user is None:
                raise HTTPException(status_code=422, detail=[NOT_FOUND])
            cols_to_upd = []
            if (
                inactive_user.status != status.value
                or comment != inactive_user.status_admin_comment
            ):
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
                        actions=None,
                    )
                if self._uservalidation:
                    user_profile = UserModelProfile.from_orm(inactive_user)
                    if self.account_validation == True and status == UserStatus.pending:
                        # reason can be empty when all validation dialog is made via email -
                        # if requested : add an admin_comment field to the user account and send it to explain what needs to be modified in the reminder to the user. ticket number can be included
                        self._uservalidation.request_user_to_modify_profile(
                            user_profile,
                            self._get_assistance_email(),
                            reason=str(comment or ""),
                            action=ActivationType.update,
                        )
                    else:
                        status_name = status.name
                        self._uservalidation.inform_user_status(
                            user_profile,
                            self._get_assistance_email(),
                            status_name=status_name,
                            reason=str(comment or ""),
                        )
        else:
            raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])

    def _refresh_any_status(
        self,
        user_id: UserIDT,
        token: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        if not self._uservalidation:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        err = True
        user: Optional[User] = None
        if user_id != -1:
            user = self.session.query(User).get(user_id)
        if user is None or user.status == UserStatus.blocked.value:
            # no action if wrong id or user is blocked
            raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])
        if token is not None:
            email = self._uservalidation.get_email_from_token(token)
            id = self._uservalidation.get_id_from_token(token)
            if (
                id > -1
                and str(email or "").lower() == str(user.email or "").lower()
                and id == user.id
            ):
                with LoginService() as sce:
                    verified = sce.verify_and_update_password(password, user)
                if not verified:
                    raise HTTPException(
                        status_code=403,
                        detail=[NOT_AUTHORIZED],
                    )
        now = DateTime.now_time()
        from datetime import timedelta, datetime

        cols_to_upd = []
        if self.verify_email == True:
            if user.mail_status != True:
                if token is None:
                    # resend emailmodification request  if it was sent more than 24h ago
                    if user.mail_status_date is None or (
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
                else:
                    update_src = UserModelWithRights.from_orm(user)
                    update_src, addcols = self._set_mail_status(update_src, True)
                    err = False
                    if len(addcols):
                        cols_to_upd.extend(addcols)
                        if (
                            self._keep_active() == True
                            and update_src.status != UserStatus.active.value
                        ):
                            update_src.status = UserStatus.active.value
                            cols_to_upd.append(User.status)

            elif self.account_validation == True:
                # mailstatus is True and account_vaidation is True
                if user.status == UserStatus.pending.value and (
                    not user.status_date
                    or (user.status_date - now) < timedelta(hours=PROFILE_TOKEN_AGE)
                ):
                    # resend request for account validation if it was sent more than PROFILE_TOKEN_AGE h ago
                    update_src = UserModelWithRights.from_orm(user)
                    if update_src.id == -1:
                        actiontype = ActivationType.create
                    else:
                        actiontype = ActivationType.update
                    self._uservalidation.request_user_to_modify_profile(
                        UserModelProfile.from_orm(user),
                        self._get_assistance_email(),
                        reason=user.status_admin_comment,
                        action=actiontype,
                    )
                    update_src.status_date = now
                    cols_to_upd.append(User.status_date)
                    err = False
            if err:
                if user.mail_status == True and user.status == UserStatus.active.value:
                    raise HTTPException(
                        status_code=400,
                        detail=[DETAIL_NOTHING_DONE],
                    )
                elif token:
                    raise HTTPException(
                        status_code=422,
                        detail=[DETAIL_NOTHING_DONE],
                    )
                else:
                    raise HTTPException(
                        status_code=422,
                        detail=[NOT_AUTHORIZED],
                    )

            elif len(cols_to_upd):
                self._model_to_db(
                    user,
                    update_src,
                    cols_to_upd=cols_to_upd,
                    actions=None,
                )
                # send activation request to users administrators
                if (
                    self.account_validation == True
                    and token is not None
                    and user.mail_status == True
                    and user.status == UserStatus.inactive.value
                ):
                    self._uservalidation.request_activate_user(
                        UserModelProfile.from_orm(user),
                        validation_emails=self._get_validation_emails(),
                        action=ActivationType.update.value,
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
                status_code=401,
                detail=[NOT_AUTHORIZED],
            )
        return verified

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
                status_code=422,
                detail=[DETAIL_VALIDATION_NOT_ACTIVE],
            )
        current_user = None
        if current_user_id is not None:
            current_user = RightsBO.get_user_throw(self.ro_session, current_user_id)
        if current_user_id is None:
            # Unauthenticated user asks to reset his password
            # Verify not a robot
            self._verify_captcha_thow(no_bot)
            # verify if the email exists  in the db
            if token is None:
                self._has_ident_user(dict({"email": resetreq.email}), True)
        # if authenticated must be admin to request the reset
        elif current_user is not None and self._current_is_admin(current_user):
            raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])
        id = -1
        if token:
            if resetreq.password is None or not UserBO.is_strong_password(
                resetreq.password
            ):
                raise HTTPException(
                    status_code=422,
                    detail=[DETAIL_PASSWORD_STRENGTH_ERROR],
                )

            email = self._uservalidation.get_email_from_token(token)
            temp_password = self._uservalidation.get_reset_from_token(token)
            user_id = self._uservalidation.get_id_from_token(token)
            err = True
            if temp_password is not None and user_id != -1:
                user_to_reset: Optional[User] = self.session.query(User).get(user_id)
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
                            temp_pw: Optional[TempPasswordReset] = self.session.query(
                                TempPasswordReset
                            ).get(user_to_reset.id)
                            self.session.delete(temp_pw)
                            self.session.commit()
                            id = user_to_reset.id
                            err = False
            if err:
                raise HTTPException(status_code=422, detail=[NOT_FOUND])

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
                        temp_rs: Optional[TempPasswordReset] = self.session.query(
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
                raise HTTPException(status_code=422, detail=[NOT_FOUND])
        return id

    def _get_assistance_email(self) -> str:
        if self._assistance_email == "":
            from_config = self.config.get_app_manager()
            if from_config[1] != None:
                self._assistance_email = str(from_config[1] or None)
            if self._assistance_email == None:
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
