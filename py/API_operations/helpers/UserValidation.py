# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# User Validation Service .
#
from typing import Optional, Any
from API_operations.helpers.Service import Service
from BO.Rights import NOT_AUTHORIZED
from DB.User import User, TempPasswordReset
from helpers.login import LoginService
from providers.MailService import MailService, ReplaceInMail
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from helpers.DynamicLogs import get_logger, LogsSwitcher
from API_operations.CRUD.Users import TempPasswordReset
from fastapi import HTTPException
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_401_UNAUTHORIZED,
)

logger = get_logger(__name__)
ACTIVATION_ACTION_CREATE = "create"
ACTIVATION_ACTION_UPDATE = "update"
ACTIVATION_ACTION_ACTIVE = "active"
ACTIVATION_ACTION_DESACTIVE = "desactive"


class UserValidationService(Service):
    """
    A service to validate user email depending on config.ini params .
    TODO: request from
    """

    def __init__(self) -> None:
        super().__init__()
        self.email_verification = self.config.get_cnf("USER_EMAIL_VERIFICATION") == "on"
        self.account_validate_email = self.config.get_cnf("ACCOUNT_VALIDATE_EMAIL")
        self.account_active = self.config.get_cnf("ACCOUNT_ACTIVE_DEFAULT")
        self.secret_key = self.config.get_cnf("MAILSERVICE_SECRET_KEY")
        # for token generation
        self.app_instance = self.config.get_cnf("INSTANCE_ID")
        if self.app_instance is None:
            self.app_instance = "EcoTaxa.01"

    #
    # verify temp password before reset
    #
    def verify_temp_password(self, temp_password: str, temp: TempPasswordReset) -> bool:
        """Returns ``True`` if the temporary password is valid for the specified user id.
        :param temp_password: A plaintext password to verify
        :param user id: The user id to verify against
        """
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
                detail=["", "Unauthorized", ""],
            )

    # call to request email_verification - validation method is by sending an email with a token
    def request_email_verification(
        self,
        email: str,
        action: str,
        id: int = -1,
        url: Optional[str] = None,
        bypass=False,
    ) -> bool:
        if bypass:
            return False
        else:
            token = self.generate_token(email, id=id, action=action)

            with MailService() as mailservice:
                mailservice.send_verification_mail(email, token, action=action, url=url)
            return True

    def request_activate_user(
        self,
        inactive_user: User,
        token: Optional[str] = None,
        action: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        if self.account_validate_email:
            if token:
                self.check_id_from_token(
                    token, email=inactive_user.email, id=inactive_user.id
                )
                action = self.get_value_from_token(token, "action")
                if action is None:
                    action = ACTIVATION_ACTION_CREATE
            with MailService() as mailservice:
                mailservice.send_activation_mail(
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

    def inform_user_activestate(self, user: User, url: Optional[str] = None) -> None:
        active = user.active
        action = ACTIVATION_ACTION_ACTIVE
        token = None
        if not active:
            action = ACTIVATION_ACTION_DESACTIVE
            token = self.generate_token(user.email, id=user.id, action=action)
        with MailService() as mailservice:
            mailservice.send_activated_mail(
                user.email, active=active, action=action, token=token, url=url
            )

    def request_reset_password(
        self, user_to_reset: User, temp_password: str, url=None
    ) -> None:
        token = self.generate_token(None, id=user_to_reset.id, action=temp_password)
        with MailService() as mailservice:
            mailservice.send_reset_password_mail(user_to_reset.email, token, url=url)

    def keepactive(self) -> bool:
        # check if external validation on registration or profile email modification
        return self.account_validate_email is None and self.account_active == True

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

    def generate_token(
        self,
        email: str,
        id: int = -1,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> str:
        tokenreq = dict({})
        tokenreq["instance"] = self.app_instance
        tokenreq["ip"] = ip
        tokenreq["email"] = email
        if id != -1:
            tokenreq["id"] = id
        if action != None:
            tokenreq["action"] = action

        token = self._build_serializer(self.secret_key).dumps(tokenreq)
        return token

    def get_value_from_token(
        self,
        token: str,
        name: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> str:
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
                detail=["", "Bad signature or expired", ""],
            )

        if self.app_instance != payload.get("instance"):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail=["", "Bad instance", ""]
            )
        value = payload.get(name)
        if (
            value
            and (name != "email" or (email == None or email == value))
            and (action == None or payload.get("action") == action)
        ):
            if ip == None or payload.get("ip") == ip:
                return value
        else:
            return None

    def get_email_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> str:
        return self.get_value_from_token(token, "email", email, ip, action)

    def get_id_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> str:
        return self.get_value_from_token(token, "id", email, ip, action)

    def get_reset_from_token(
        self,
        token: str,
        email: Optional[str] = None,
        ip: Optional[str] = None,
        action: Optional[str] = None,
    ) -> str:
        # the temp_password is stored into action field of the token
        return self.get_value_from_token(token, "action", email, ip, action)

    def check_id_from_token(self, token: str, email: str, id: int) -> None:
        try:
            payload = self._build_serializer(self.secret_key).loads(
                token, max_age=1 * 3600
            )
        except:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=["", "Bad signature - token for creation has expired", ""],
            )

        if (
            payload.get("instance") != self.app_instance
            or payload.get("email") != email
            or payload.get("id") != id
        ):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail=["", "Invalid token", ""]
            )


class ValidationException(Exception):
    pass
