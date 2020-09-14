# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Utils for configuring fastApi
#
import sys
import traceback
from os.path import dirname
from typing import Any

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import URLSafeTimedSerializer, TimestampSigner, SignatureExpired, BadSignature

from helpers.link_to_legacy import read_config
from .starlette import status, PlainTextResponse


async def internal_server_error_handler(_request: Any, exc: Exception) -> PlainTextResponse:
    """
        Override internal error handler, so that we don't have to look at logs on server side in case of problem.
    :param _request:
    :param exc: The exception caught.
    :return:
    """
    tpe, val, tbk = sys.exc_info()
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    tb = traceback.format_exception(tpe, val, tbk)
    our_stack_ndx = 0
    # Remove all until our code
    for ndx, a_line in enumerate(tb):
        if a_line.find("main.py") != -1:
            our_stack_ndx = ndx
            break
    data = "\n----------- BACK-END -------------\n" + "".join(tb[our_stack_ndx:])
    return PlainTextResponse(data, status_code=status_code)


# In a development environment, dump the API definition at each run
def dump_openapi(app: FastAPI, main_path: str): # pragma: no cover
    import sys
    if "--reload" not in sys.argv:
        return  # It's not dev
    import json
    from pathlib import Path
    json_def = json.dumps(app.openapi(),
                          ensure_ascii=False,
                          allow_nan=False,
                          indent=2,
                          separators=(",", ":"))
    # Copy here for Git commit but also into another dev tree
    parent_dir = dirname(main_path)
    dests = [Path(parent_dir, "..", "openapi.json"),
             Path(parent_dir, "..", "..", "ecotaxa_master", "to_back", "openapi.json")]
    for dest in dests:
        with dest.open("w") as fd:
            fd.write(json_def)


secured_scheme = HTTPBearer()

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

MAX_TOKEN_AGE = 2678400  # max token age, 31 days

_serializer = None


def _build_serializer():
    global _serializer
    if not _serializer:
        # Read from legacy app config
        secret_key = read_config()['SECRET_KEY'][1:-1]
        # Hardcoded in Flask
        salt = b"cookie-session"
        _serializer = URLSafeTimedSerializer(secret_key=secret_key, salt=salt,
                                             signer=TimestampSigner,
                                             signer_kwargs={'key_derivation': 'hmac'})
    return _serializer


def _get_current_user(scheme, credentials) -> int:  # pragma: no cover
    """
        Extract current user from auth string, anything going wrong means security exception.
        Not reasonable to test automatically, so excluded from code coverage measurement.
    """
    try:
        if scheme != 'Bearer':
            raise _credentials_exception
        payload = _build_serializer().loads(credentials, max_age=MAX_TOKEN_AGE)
        try:
            ret: int = int(payload["user_id"])
        except (KeyError, ValueError):
            raise _credentials_exception
    except (SignatureExpired, BadSignature):
        raise _credentials_exception
    if ret < 0:
        raise _credentials_exception
    return ret


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(secured_scheme)) -> int:
    """
        Just relay the call to the private def above.
    """
    return _get_current_user(creds.scheme, creds.credentials)


_forbidden_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You can't do this."
)

_not_found_exception = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Not found."
)


class RightsThrower(object):
    """
        Transform any AssertionError, during exit block of "with" syntax, into an HTTP error.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # An exception was thrown
            if exc_type == AssertionError:
                if exc_val.args:
                    if exc_val.args[0] == "Not authorized":
                        raise _forbidden_exception
                    elif exc_val.args[0] == "Not found":
                        raise _not_found_exception
            # Re-raise
            raise Exception(str(exc_val)).with_traceback(exc_tb)
