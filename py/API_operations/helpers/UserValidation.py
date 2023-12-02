# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# User Validation Service .
#
from typing import Optional, Any, Final, List
from enum import Enum
from BO.Rights import NOT_AUTHORIZED
from BO.User import UserIDT, SHORT_TOKEN_AGE, PROFILE_TOKEN_AGE
from API_models.crud import UserModelProfile
from helpers.AppConfig import Config
from providers.MailProvider import MailProvider
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from helpers.DynamicLogs import get_logger
from fastapi import HTTPException
from helpers.httpexception import DETAIL_BAD_INSTANCE, DETAIL_BAD_SIGN_OR_EXP

logger = get_logger(__name__)


class ActivationType(str, Enum):
    create: Final = "create"
    update: Final = "update"
    status: Final = "status "
    inform: Final = "inform"
    passwordreset: Final = "passwordreset"


class UserValidation(object):
    """
    Manage User validation
    TODO: request from different clients url
    """

    def __init__(self):
        # email verification
        config = Config()
        # unset status field "active" value if major modification is done by anyone except users admin
        # 0 email - 1 pwd - 2 - dns - 3 port
        self.senderaccount = str(config.get_sender_account() or "").split(",")
        self._mailservice_salt = config.get_mailservice_salt()
        self._mailprovider = MailProvider(
            self.senderaccount,
            config.get_dir_mail_templates(),
            SHORT_TOKEN_AGE,
            PROFILE_TOKEN_AGE,
            config.get_add_ticket(),
        )
        self.secret_key = str(config.get_cnf("MAILSERVICE_SECRET_KEY") or "")
        self.app_instance_id = str(config.get_cnf("INSTANCE_ID") or "EcoTaxa.01")
        self._request_url = str(config.get_account_request_url())

    # call to request email_verification - validation method is by sending an email with a token

    def request_email_verification(
        self,
        email: str,
        assistance_email: str,
        action: ActivationType,
        id: int,
        previous_email: Optional[str],
        url: Optional[str] = None,
    ) -> bool:
        token = self._generate_token(email, id=id, action=action.value)
        if previous_email == email:
            previous_email = None
        self._mailprovider.send_verification_mail(
            email,
            assistance_email,
            token,
            action=action.value,
            previous_email=previous_email,
            url=self.get_request_url(url),
        )
        logger.info("Verification email sent  :  '%s'" % email)
        return True

    def request_activate_user(
        self,
        inactive_user: UserModelProfile,
        validation_emails: List[str],
        action: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        if action is None:
            action = ActivationType.create.value
        self._mailprovider.send_activation_request_mail(
            validation_emails,
            data={
                "id": inactive_user.id,
                "name": inactive_user.name,
                "email": inactive_user.email,
                "organisation": inactive_user.organisation,
                "creationreason": inactive_user.usercreationreason,
            },
            action=action,
            url=self.get_request_url(url),
        )
        logger.info(
            "Request activation user %s  mail sent :  '%s'"
            % (str(inactive_user.id), inactive_user.email)
        )

    def inform_user_status(
        self,
        user: UserModelProfile,
        assistance_email: str,
        status_name: str,
        reason: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        from DB.User import UserStatus

        if status_name == UserStatus.pending.name:
            token = self._generate_token(
                user.email, id=user.id, action=ActivationType.status.value
            )
        else:
            token = None
        self._mailprovider.send_status_mail(
            user.email,
            assistance_email,
            status_name=status_name,
            action=ActivationType.status.value,
            token=token,
            reason=reason,
            url=self.get_request_url(url),
        )
        logger.info(
            " inform user status  %s mail sent :  '%s'" % (status_name, user.email)
        )

    def request_user_to_modify_profile(
        self,
        user: UserModelProfile,
        assistance_email: str,
        reason: str,
        action: ActivationType = ActivationType.create,
        url: Optional[str] = None,
    ) -> None:

        # exception user email and id in the same token - for mod after creation and active is False
        token = self._generate_token(
            id=user.id, email=user.email, action=action.value, reason=reason
        )
        self._mailprovider.send_hastomodify_mail(
            user.email,
            assistance_email,
            reason=reason,
            action=action.value,
            token=token,
            url=self.get_request_url(url),
        )
        logger.info(" request user to modify profile email sent :  '%s'" % user.email)

    def request_reset_password(
        self,
        user_to_reset: UserModelProfile,
        assistance_email: str,
        temp_password: str,
        url: Optional[str] = None,
    ) -> None:
        token = self._generate_token(id=user_to_reset.id, action=temp_password)
        self._mailprovider.send_reset_password_mail(
            user_to_reset.email, assistance_email, token, url=self.get_request_url(url)
        )
        logger.info("reset password email sent :  '%s'" % user_to_reset.email)

    def get_request_url(self, url: Optional[str]) -> str:
        if url is None:
            return self._request_url
        return url

    def is_valid_email(self, email: str) -> bool:
        return self._mailprovider.is_email(email)

    @staticmethod
    def _build_serializer(secret_key: str, salt: str) -> URLSafeTimedSerializer:

        from itsdangerous import TimestampSigner

        _mailserializer = URLSafeTimedSerializer(
            secret_key=secret_key,
            salt=salt.encode("UTF-8"),
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
        if email is not None:
            tokenreq["email"] = email
        if ip is not None:
            tokenreq["ip"] = ip
        if id != -1:
            tokenreq["id"] = str(id)
        if action is not None:
            tokenreq["action"] = action
        if reason is not None:
            tokenreq["reason"] = reason
        return str(
            self._build_serializer(self.secret_key, self._mailservice_salt).dumps(
                tokenreq
            )
            or ""
        )

    def _get_value_from_token_throw(
        self,
        token: str,
        name: str,
        short: Optional[bool] = True,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[str]:
        try:
            if short == True:
                age = SHORT_TOKEN_AGE
            else:
                age = PROFILE_TOKEN_AGE
            payload = self._build_serializer(
                self.secret_key, self._mailservice_salt
            ).loads(token, max_age=int(age) * 3600)
        except (SignatureExpired, BadSignature):
            raise HTTPException(
                status_code=403,
                detail=[DETAIL_BAD_SIGN_OR_EXP],
            )
            return
        if self.app_instance_id != payload.get("instance"):
            raise HTTPException(status_code=403, detail=[DETAIL_BAD_INSTANCE])
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
        short: Optional[bool] = True,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[str]:
        return self._get_value_from_token_throw(
            token, "email", short, email, ip, action
        )

    def get_id_from_token(
        self,
        token: str,
        short: Optional[bool] = True,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> int:
        return int(
            self._get_value_from_token_throw(token, "id", short, email, ip, action)
            or -1
        )

    def get_reset_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[str]:
        # the temp_password is stored into action field of the token
        return self._get_value_from_token_throw(
            token, "action", True, email, ip, action
        )


class ValidationException(Exception):
    """
    TODO - manage HTTPExceptions
    """

    pass
