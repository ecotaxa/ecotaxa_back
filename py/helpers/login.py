# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Login validation and token management.
#
import base64
import hashlib
import hmac
from typing import Union, Optional

# Note: passlib uses in Python3.14 a python implementation of crypto algos
# as 'crypt' module has been deprecated. It's a bit slower and eats lots of CPUs.
# but we use it only at each login or account creation. The rest is JWT.
from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from API_operations.helpers.Service import Service
from BO.Rights import NOT_AUTHORIZED
from BO.User import UserBO
from DB.User import User, UserStatus, UserQuality
from helpers.AppConfig import Config, ConfigKey
from helpers.fastApiUtils import build_serializer

NOT_AUTHORIZED_MAIL = "__id____" + NOT_AUTHORIZED


class PasswordHasher(object):
    """
    Password hashing and verification without opening DB connections.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        pw_hash = self.config.get_security_password_hash()
        assert pw_hash is not None, "SECURITY_PASSWORD_HASH not set!"
        schemes = [pw_hash, "plaintext"]
        deprecated = ["auto"]
        self.pwd_context = CryptContext(
            schemes=schemes, default=pw_hash, deprecated=deprecated
        )
        # Hashing config
        self.password_salt = self.config.get_security_password_salt()
        self.password_hash = None

    def verify_and_update_password(
        self, password: str, user: User, session: Session
    ) -> bool:
        """Returns ``True`` if the password is valid for the specified user.

        Additionally, the hashed password in the database is updated if the
        hashing algorithm happens to have changed.

        :param password: A plaintext password to verify
        :param user: The user to verify against
        :param session: DB session to commit password hash upgrade if needed
        """
        if self.use_double_hash(user.password):
            # Core of the job: comparing DB user.password with same-method encoding of the given password
            verified = self.pwd_context.verify(self.get_hmac(password), user.password)
        else:
            # Try with plaintext password.
            verified = self.pwd_context.verify(password, user.password)

        if (
            verified
            and user.password is not None
            and self.pwd_context.needs_update(user.password)
        ):
            # Write a more secure version
            user.password = self.hash_password(password)
            session.commit()
        return verified

    def hash_password(self, password: str) -> str:
        """Hash the specified plaintext password.

        It uses the configured hashing options.

        .. versionadded:: 2.0.2

        :param password: The plaintext password to hash
        """
        if self.use_double_hash():
            password = self.get_hmac(password).decode("ascii")

        return self.pwd_context.hash(password)

    def get_hmac(self, password: str) -> bytes:
        """Returns a Base64 encoded HMAC+SHA512 of the password signed with
        the salt specified by ``SECURITY_PASSWORD_SALT``.

        :param password: The password to sign
        """
        salt = self.password_salt

        if salt is None:
            raise RuntimeError(
                "The configuration value `SECURITY_PASSWORD_SALT` must "
                "not be None when the value of `SECURITY_PASSWORD_HASH` is "
                'set to "%s"' % self.password_hash
            )  # pragma:nocover

        h = hmac.new(
            self.encode_string(salt), self.encode_string(password), hashlib.sha512
        )
        return base64.b64encode(h.digest())

    @staticmethod
    def encode_string(string: Union[str, bytes]) -> bytes:
        """Encodes a string to bytes, if it isn't already.

        :param string: The string to encode"""

        if isinstance(string, str):
            string = string.encode("utf-8")
        return string

    def use_double_hash(self, password_hash: Optional[str] = None) -> bool:
        """Return a bool indicating whether a password should be hashed twice."""
        single_hash = (
            ConfigKey.PASSWORD_SINGLE_HASH in self.config.list_cnf()
        )  # Not the case in EcoTaxa config
        if single_hash and self.password_salt:
            raise RuntimeError(
                "You may not specify a salt with " "SECURITY_PASSWORD_SINGLE_HASH"
            )  # pragma:nocover

        if password_hash is None:
            is_plaintext = self.password_hash == "plaintext"
        else:
            is_plaintext = self.pwd_context.identify(password_hash) == "plaintext"

        return not (is_plaintext or single_hash)


class LoginService(Service):
    """
    A service to validate login via the API.
    TODO: It's crypto, so without cache, it might not be fast. To measure.
    """

    def __init__(self) -> None:
        super().__init__()
        self._pw_hasher = PasswordHasher(self.config)
        self.pwd_context = self._pw_hasher.pwd_context
        self.password_salt = self._pw_hasher.password_salt
        self.password_hash = self._pw_hasher.password_hash

    def validate_login(self, username: str, password: str) -> Union[str, bytes]:
        """Legacy /login: a long-lived token, signed with the Flask salt."""
        the_user = self.authenticate(username, password)
        return build_serializer().dumps({"user_id": the_user.id})

    def authenticate(self, username: str, password: str) -> User:
        # Fetch the one and only user
        # username is an email - check before
        assert username is not None, NOT_AUTHORIZED
        account_validation = self.config.get_account_validation() == "on"
        # if account validation is "on" and account is pending

        user_qry = select(User)
        user_qry = user_qry.where(func.lower(User.email).__eq__(func.lower(username)))
        if account_validation is True:
            pass
        else:
            user_qry = user_qry.where(User.status == UserStatus.active.value)
        db_users = self.session.execute(user_qry).scalars().all()
        assert len(db_users) == 1, NOT_AUTHORIZED
        the_user: User = db_users[0]
        # verif even user is not active , in order to let modify email only if mail_status is False
        verif_ok = self.verify_and_update_password(password, the_user)
        assert verif_ok == True, NOT_AUTHORIZED
        is_strong = UserBO.is_strong_password(password)
        # Check if record already exists
        quality = (
            self.session.query(UserQuality)
            .filter(UserQuality.user_id == the_user.id)
            .first()
        )
        if quality:
            quality.password_strong = is_strong
        else:
            quality = UserQuality(user_id=the_user.id, password_strong=is_strong)
            self.session.add(quality)
        self.session.commit()
        # throw exception if the user is not active
        self.verify_status_throw(the_user, account_validation)
        return the_user

    #
    # Copy/paste/adapt from flask-security
    #
    def verify_and_update_password(self, password, user) -> bool:
        return self._pw_hasher.verify_and_update_password(password, user, self.session)

    def hash_password(self, password):
        return self._pw_hasher.hash_password(password)

    def get_hmac(self, password):
        return self._pw_hasher.get_hmac(password)

    @staticmethod
    def encode_string(string):
        return PasswordHasher.encode_string(string)

    def use_double_hash(self, password_hash=None) -> bool:
        return self._pw_hasher.use_double_hash(password_hash)

    @staticmethod
    def verify_status_throw(the_user: User, account_validation: bool):
        """
        If account validation is on "on" returns only the necessary data to modify a profile or request new confirmation mails
        """
        if account_validation is True and the_user.status != UserStatus.active.value:
            from fastapi import HTTPException

            if the_user.status == UserStatus.pending.value:
                # remove sensible infos
                userdata = the_user.__dict__
                for key in [
                    "password",
                    "_sa_instance_state",
                    "mail_status",
                    "status_date",
                    "mail_status_date",
                    "usercreationdate",
                    "preferences",
                ]:
                    del userdata[key]
            else:
                userdata = {
                    "id": the_user.id,
                    "status": the_user.status,
                    "mail_status": the_user.mail_status,
                }

            detail = userdata
            raise HTTPException(
                status_code=401,
                detail=[detail],
            )
        assert the_user.status == UserStatus.active.value, NOT_AUTHORIZED
