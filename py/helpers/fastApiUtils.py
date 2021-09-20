# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Utils for configuring fastApi
#
import json
import logging
import sys
import traceback
from os.path import dirname
from typing import Any, Optional, Dict, List

import orjson
from fastapi import FastAPI, Depends, HTTPException
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from itsdangerous import URLSafeTimedSerializer, TimestampSigner, SignatureExpired, BadSignature  # type: ignore
# noinspection PyPackageRequirements
from starlette.requests import Request
# noinspection PyPackageRequirements
from starlette.responses import JSONResponse
# noinspection PyPackageRequirements
from starlette.status import HTTP_403_FORBIDDEN

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
def dump_openapi(app: FastAPI, main_path: str):  # pragma: no cover
    import sys
    if "uvicorn" not in sys.argv:
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


class BearerOrCookieAuth(OAuth2):
    """
        Credits to https://medium.com/data-rebels/fastapi-how-to-add-basic-and-cookie-authentication-a45c85ef47d3
    """

    def __init__(
            self,
            tokenUrl: str,
            scheme_name: str = None,
            scopes: dict = None,
            auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        header_authorization: str = request.headers.get("Authorization")
        session_cookie: Optional[str] = request.cookies.get("session")

        header_scheme, header_param = get_authorization_scheme_param(
            header_authorization
        )

        if header_scheme.lower() == "bearer":
            return header_param
        elif session_cookie is not None:
            return session_cookie
        else:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            else:
                return None


mixed_scheme = BearerOrCookieAuth(tokenUrl="/token")
# The same but not throwing an exception if user is not authenticated.
# used for cases when authentication is optional
mixed_scheme_nothrow = BearerOrCookieAuth(tokenUrl="/token", auto_error=False)

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

MAX_TOKEN_AGE = 2678400  # max token age, 31 days

_serializer = None


def build_serializer():
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


def _get_current_user(token) -> int:  # pragma: no cover
    """
        Extract current user from auth string, anything going wrong means security exception.
        Not reasonable to test automatically, so excluded from code coverage measurement.
    """
    try:
        payload = build_serializer().loads(token, max_age=MAX_TOKEN_AGE)
        try:
            ret: int = int(payload["user_id"])
        except (KeyError, ValueError):
            raise _credentials_exception
    except (SignatureExpired, BadSignature):
        raise _credentials_exception
    if ret < 0:
        raise _credentials_exception
    return ret


async def get_optional_current_user(token: str = Depends(mixed_scheme_nothrow)) \
        -> Optional[int]:  # pragma: no cover
    """
        There _can_ be a user in the request, get the id if the case.
    """
    if token is None:
        return None
    try:
        return _get_current_user(token)
    except HTTPException:
        return None


async def get_current_user(token: str = Depends(mixed_scheme)) -> int:
    """
        Just relay the call to the private def above.
    """
    return _get_current_user(token)


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

    def __init__(self):
        pass

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


class ValidityThrower(object):
    """
        Transform any AssertionError, during exit block of "with" syntax,
        into a HTTP 422 error.
    """

    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # An exception was thrown
            if exc_type == AssertionError:
                if exc_val.args:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc_val.args[0])
            # Re-raise
            raise Exception(str(exc_val)).with_traceback(exc_tb)


class MyORJSONResponse(JSONResponse):
    """
        A copy/paste of ORJSONResponse but setting some permissive parameters on the 'dumps' call.
    """
    media_type = "application/json"

    type_to_fields: Dict[Any, List[str]] = {}

    @classmethod
    def register(cls, a_class, its_model):
        cls.type_to_fields[a_class] = list(its_model.__fields__.keys())

    @classmethod
    def orjson_default(cls, obj):
        # ORJSon calls this method when it cannot serialize an object.
        # We mimic FastApi behavior of fetching data from the object using the model fields
        fields = cls.type_to_fields.get(obj.__class__)
        if fields is None:
            raise TypeError
        ret = {fld: getattr(obj, fld) for fld in fields}
        return ret

    try:
        import orjson

        def render(self, content: Any) -> bytes:
            try:
                return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS,
                                    default=MyORJSONResponse.orjson_default)
            except TypeError:
                logging.warning("Problem encoding %s", content)
                return json.dumps(content)

    except ImportError:
        # noinspection PyUnusedLocal
        def render(self, content: Any) -> bytes:
            assert False, "orjson must be installed to use ORJSONResponse"
            # noinspection PyUnreachableCode
            return bytes()
