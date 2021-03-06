# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Login validation and token management.
#
import base64
import hashlib
import hmac

# TODO: if it exists, find the stubs somewhere
from passlib.context import CryptContext  # type: ignore

from API_operations.helpers.Service import Service
from BO.Rights import NOT_AUTHORIZED
from DB import User
from helpers.fastApiUtils import build_serializer


class LoginService(Service):
    """
        A service to validate login via the API.
        TODO: It's crypto, so without cache, it's not fast. Not ready for replacing Flask one.
    """

    def __init__(self):
        super().__init__()
        # Hashing algos
        pw_hash = self.config.get("SECURITY_PASSWORD_HASH")
        assert pw_hash is not None, "SECURITY_PASSWORD_HASH not set!"
        schemes = [pw_hash, 'plaintext']
        deprecated = ['auto']
        self._pwd_context = CryptContext(
            schemes=schemes,
            default=pw_hash,
            deprecated=deprecated)
        # Hashing config
        self.password_salt = self.config.get("SECURITY_PASSWORD_SALT")
        self.password_hash = None

    def validate_login(self, username: str, password: str) -> str:
        # Fetch the one and only user
        user_qry = self.session.query(User).filter(User.email == username).filter(User.active)
        db_users = user_qry.all()
        assert len(db_users) == 1, NOT_AUTHORIZED
        the_user: User = db_users[0]
        #
        verif_ok = self.verify_and_update_password(password, the_user)
        assert verif_ok, NOT_AUTHORIZED
        # Sign with the verifying serializer, the salt is Flask's one
        token = build_serializer().dumps({"user_id": the_user.id})
        return token

    #
    # Copy/paste/adapt from flask-security
    #
    def verify_and_update_password(self, password, user):
        """Returns ``True`` if the password is valid for the specified user.

        Additionally, the hashed password in the database is updated if the
        hashing algorithm happens to have changed.

        :param password: A plaintext password to verify
        :param user: The user to verify against
        """
        if self.use_double_hash(user.password):
            # Core of the job: comparing DB user.password with same-method encoding of the given password
            verified = self._pwd_context.verify(self.get_hmac(password), user.password)
        else:
            # Try with plaintext password.
            verified = self._pwd_context.verify(password, user.password)

        if verified and self._pwd_context.needs_update(user.password):
            # Write a more secure version
            user.password = self.hash_password(password)
            self.session.commit()
        return verified

    def hash_password(self, password):
        """Hash the specified plaintext password.

        It uses the configured hashing options.

        .. versionadded:: 2.0.2

        :param password: The plaintext password to hash
        """
        if self.use_double_hash():
            password = self.get_hmac(password).decode('ascii')

        return self._pwd_context.hash(password)
        #     **self.config.get('PASSWORD_HASH_OPTIONS', default={}).get(
        #         self.password_hash, {})
        # )

    def get_hmac(self, password):
        """Returns a Base64 encoded HMAC+SHA512 of the password signed with
        the salt specified by ``SECURITY_PASSWORD_SALT``.

        :param password: The password to sign
        """
        salt = self.password_salt

        if salt is None:
            raise RuntimeError(
                'The configuration value `SECURITY_PASSWORD_SALT` must '
                'not be None when the value of `SECURITY_PASSWORD_HASH` is '
                'set to "%s"' % self.password_hash)  # pragma:nocover

        h = hmac.new(self.encode_string(salt), self.encode_string(password), hashlib.sha512)
        return base64.b64encode(h.digest())

    @staticmethod
    def encode_string(string):
        """Encodes a string to bytes, if it isn't already.

        :param string: The string to encode"""

        if isinstance(string, str):
            string = string.encode('utf-8')
        return string

    def use_double_hash(self, password_hash=None):
        """Return a bool indicating whether a password should be hashed twice."""
        single_hash = 'PASSWORD_SINGLE_HASH' in self.config  # Not the case in EcoTaxa config
        if single_hash and self.password_salt:
            raise RuntimeError('You may not specify a salt with '
                               'SECURITY_PASSWORD_SINGLE_HASH')  # pragma:nocover

        if password_hash is None:
            is_plaintext = self.password_hash == 'plaintext'
        else:
            is_plaintext = self._pwd_context.identify(password_hash) == 'plaintext'

        return not (is_plaintext or single_hash)
