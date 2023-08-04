# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# User Validation Service .
#
from typing import Optional, Any
from BO.Rights import NOT_AUTHORIZED
from BO.User import UserIDT
from API_models.crud import UserModelProfile
from helpers.login import LoginService
from helpers.AppConfig import Config
from providers.MailProvider import MailProvider, ReplaceInMail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from helpers.DynamicLogs import get_logger, LogsSwitcher

from fastapi import HTTPException
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_401_UNAUTHORIZED,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

logger = get_logger(__name__)

ACTIVATION_ACTION_CREATE = "create"
ACTIVATION_ACTION_UPDATE = "update"
ACTIVATION_ACTION_ACTIVE = "active"
ACTIVATION_ACTION_DESACTIVE = "desactive"
ACTIVATION_ACTION_HASTOMODIFY = "modify"


class UserValidation(object):
    """
    Manage User validation
    TODO: request from different clients url
    """

    def __init__(self):
        # email verification
        config = Config()
        self.verify_email = config.get_cnf("USER_EMAIL_VERIFICATION") == "on"
        # external activation of account - only one user admin can activate an account and set mail_status to verified
        self.account_activate_email = config.get_cnf("ACCOUNT_ACTIVATE_EMAIL")

        # unset active field if major mod is done by anyone except the account_activate_email ( user admin with the same email) or anyone except users admin
        self.active_unset = config.get_cnf("ACCOUNT_ACTIVE_UNSET") == True
        # 0 email - 1 pwd - 2 - dns - 3 port
        self.senderaccount: list = str(config.get_cnf("SENDER_ACCOUNT") or "").split(
            ","
        )
        self._mailprovider = MailProvider(
            self.senderaccount, self.account_activate_email
        )
        self.secret_key = str(config.get_cnf("MAILSERVICE_SECRET_KEY") or "")
        self.app_instance_id = str(config.get_cnf("INSTANCE_ID") or "EcoTaxa.01")

    def __call__(self) -> Optional[object]:
        if self.verify_email:
            if self._mailprovider is None:
                HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=["smtp is off"]
                )
            return self
        return None

    # condition to keep user activated even if major change occured

    def keep_active(self, email: Optional[str], is_admin: bool) -> bool:
        # no current_user
        if email is None:
            return not (self.verify_email and not self.active_unset)
        is_admin = is_admin and (
            self.account_activate_email is None or self.account_activate_email == email
        )
        return self.verify_email == False or (is_admin and self.active_unset == False)

    # call to request email_verification - validation method is by sending an email with a token

    def request_email_verification(
        self,
        email: str,
        action: str,
        id: int,
        url: Optional[str] = None,
        bypass=False,
    ) -> bool:
        if bypass or not self.verify_email:
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
                action = ACTIVATION_ACTION_CREATE
        self._mailprovider.send_activation_mail(
            self.account_activate_email,
            {
                "id": inactive_user.id,
                "name": inactive_user.name,
                "email": inactive_user.email,
                "organisation": inactive_user.organisation,
                "creationreason": inactive_user.usercreationreason,
            },
            action=action,
            url=url,
        )

    def inform_user_activestate(
        self, user: UserModelProfile, url: Optional[str] = None
    ) -> None:
        active = user.active
        action = ACTIVATION_ACTION_ACTIVE
        token = None
        if not active:
            action = ACTIVATION_ACTION_DESACTIVE
            token = self._generate_token(user.email, id=user.id, action=action)
        self._mailprovider.send_activated_mail(
            user.email, active=active, action=action, token=token, url=url
        )

    def request_user_to_modify_profile(
        self, user: UserModelProfile, reason: str, url: Optional[str] = None
    ) -> None:
        action = ACTIVATION_ACTION_HASTOMODIFY
        token = self._generate_token(id=user.id, action=action)
        self._mailprovider.send_hastomodify_mail(
            user.email, reason=reason, action=action, token=token, url=url
        )

    def request_reset_password(
        self,
        user_to_reset: UserModelProfile,
        temp_password: str,
        url: Optional[str] = None,
    ) -> None:
        token = self._generate_token(id=user_to_reset.id, action=temp_password)
        self._mailprovider.send_reset_password_mail(user_to_reset.email, token, url=url)

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
    ) -> str:
        tokenreq = dict({})
        tokenreq["instance"] = self.app_instance_id
        tokenreq["ip"] = ip
        tokenreq["email"] = email
        if id != -1:
            tokenreq["id"] = str(id)
        if action != None:
            tokenreq["action"] = action
        return str(self._build_serializer(self.secret_key).dumps(tokenreq) or "")

    def _get_value_from_token(
        self,
        token: str,
        name: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[str]:
        if name == "id":
            age = 4
        else:
            age = 24
        try:

            payload = self._build_serializer(self.secret_key).loads(
                token, max_age=age * 3600
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
    ) -> Optional[str]:
        return self._get_value_from_token(token, "email", email, ip, action)

    def get_id_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> int:
        return int(self._get_value_from_token(token, "id", email, ip, action) or -1)

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
