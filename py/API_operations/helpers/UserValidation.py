# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# User Validation Service .
#
from typing import Optional, Any, Final
from collections import namedtuple
from BO.Rights import NOT_AUTHORIZED
from BO.User import UserIDT, USER_PWD_REGEXP
from API_models.crud import UserModelProfile
from helpers.AppConfig import Config
from providers.MailProvider import MailProvider
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from helpers.DynamicLogs import get_logger
from fastapi import HTTPException
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_401_UNAUTHORIZED,
    HTTP_422_UNPROCESSABLE_ENTITY,
)


logger = get_logger(__name__)
SHORT_TOKEN_AGE = 1
PROFILE_TOKEN_AGE = 24

ActivationType = namedtuple(
    "ActivationType", ["create", "update", "status", "inform", "passwordreset"]
)
ACTIVATION_TYPE: Final = ActivationType(
    "create", "update", "status", "inform", "passwordreset"
)


def _get_validation_emails() -> list:
    return ["beatrice.caraveo@imev-mer.fr"]
    from API_operations.CRUD.Users import UserService

    adminlist = []
    with UserService() as sce:
        users_admins = sce.get_users_admins()
    if len(users_admins) > 0:
        adminlist = [u.email for u in users_admins]
    return adminlist


class UserValidation(object):
    """
    Manage User validation
    TODO: request from different clients url
    """

    def __init__(self):
        # email verification
        config = Config()
        # unset status field "active" value if major modification is done by anyone except users admin
        self.account_validation = config.get_account_validation() == "on"
        # 0 email - 1 pwd - 2 - dns - 3 port
        self.senderaccount: list = str(config.get_sender_account() or "").split(",")
        self._mailprovider = MailProvider(
            self.senderaccount, config.get_dir_mail_templates()
        )
        self.secret_key = str(config.get_cnf("MAILSERVICE_SECRET_KEY") or "")
        self.app_instance_id = str(config.get_cnf("INSTANCE_ID") or "EcoTaxa.01")

    # condition to keep user activated even if major change occured
    def keep_active(self, current_user_email: Optional[str], is_admin: bool) -> bool:
        # no current_user
        if current_user_email is None:
            return not self.account_validation
        return is_admin or not self.account_validation

    # call to request email_verification - validation method is by sending an email with a token

    def request_email_verification(
        self,
        email: str,
        action: str,
        id: int,
        url: Optional[str] = None,
        bypass=False,
    ) -> bool:
        if bypass:
            return False
        else:
            token = self._generate_token(email, id=id, action=action)
            self._mailprovider.send_verification_mail(
                email, token, action=action, url=url
            )
            return True

    def request_activate_user(
        self,
        inactive_user: UserModelProfile,
        token: Optional[str] = None,
        action: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        if token:
            action = self._get_value_from_token(token, "action")
            if action is None:
                action = ACTIVATION_TYPE.create
        self._mailprovider.send_activation_request_mail(
            _get_validation_emails(),
            data={
                "id": inactive_user.id,
                "name": inactive_user.name,
                "email": inactive_user.email,
                "organisation": inactive_user.organisation,
                "creationreason": inactive_user.usercreationreason,
            },
            action=action,
            url=url,
        )

    def inform_user_status(
        self, user: UserModelProfile, status: Optional[str], url: Optional[str] = None
    ) -> None:

        if status is not None:
            token = self._generate_token(
                user.email, id=user.id, action=ACTIVATION_TYPE.status
            )
        else:
            token = None
        self._mailprovider.send_status_mail(
            user.email,
            status=status,
            action=ACTIVATION_TYPE.status,
            token=token,
            url=url,
        )

    def request_user_to_modify_profile(
        self,
        user: UserModelProfile,
        reason: str,
        action: Optional[str] = ACTIVATION_TYPE.create,
        url: Optional[str] = None,
    ) -> None:

        # exception user email and id in the same token - for mod after creation and active is False
        token = self._generate_token(
            id=user.id, email=user.email, action=action, reason=reason
        )
        self._mailprovider.send_hastomodify_mail(
            user.email,
            reason=reason,
            action=action,
            token=token,
            url=url,
        )

    def request_reset_password(
        self,
        user_to_reset: UserModelProfile,
        temp_password: str,
        url: Optional[str] = None,
    ) -> None:
        token = self._generate_token(id=user_to_reset.id, action=temp_password)
        self._mailprovider.send_reset_password_mail(user_to_reset.email, token, url=url)

    def is_valid_email(self, email: str) -> bool:
        return self._mailprovider.is_email(email)

    @staticmethod
    def is_strong_password(password: str) -> bool:
        from re import match

        if match(USER_PWD_REGEXP, password):
            return True
        return False

    @staticmethod
    def _build_serializer(secret_key: str) -> URLSafeTimedSerializer:

        from itsdangerous import TimestampSigner

        salt = b"mailservice_salt"
        _mailserializer = URLSafeTimedSerializer(
            secret_key=secret_key,
            salt=salt,
            signer=TimestampSigner,
            # signer_kwargs={"key_derivation": "hmac"},
        )
        return _mailserializer

    def _generate_token(
        self,
        email: Optional[str] = None,
        id: int = -1,
        ip: Optional[str] = None,
        action: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> str:
        tokenreq = dict({})
        tokenreq["instance"] = self.app_instance_id
        tokenreq["ip"] = ip
        tokenreq["email"] = email
        if id != -1:
            tokenreq["id"] = str(id)
        if action != None:
            tokenreq["action"] = action
        if reason != None:
            tokenreq["reason"] = reason
        return str(self._build_serializer(self.secret_key).dumps(tokenreq) or "")

    def _get_value_from_token(
        self,
        token: str,
        name: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
        age: Optional[int] = None,
    ) -> Optional[str]:
        try:
            if age is None:
                age = SHORT_TOKEN_AGE
            payload = self._build_serializer(self.secret_key).loads(
                token, max_age=int(age) * 3600
            )
        except (SignatureExpired, BadSignature):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Bad signature or expired",
            )
            return
        if self.app_instance_id != payload.get("instance"):
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Bad instance")
        value = payload.get(name)
        if (
            value
            and (name != "email" or (email == None or email == value))
            and (action == None or payload.get("action") == action)
        ):
            if ip == None or payload.get("ip") == ip:
                return value
        return None

    def get_email_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
        age: Optional[int] = SHORT_TOKEN_AGE,
    ) -> Optional[str]:
        return self._get_value_from_token(token, "email", email, ip, action, age)

    def get_id_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
        age: Optional[int] = SHORT_TOKEN_AGE,
    ) -> int:
        return int(
            self._get_value_from_token(token, "id", email, ip, action, age) or -1
        )

    def get_reset_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[str]:
        # the temp_password is stored into action field of the token
        return self._get_value_from_token(token, "action", email, ip, action)


class ValidationException(Exception):
    """
    TODO - manage HTTPExceptions
    """

    pass
