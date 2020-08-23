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
def dump_openapi(app: FastAPI, main_path: str):
    import sys
    if "--reload" not in sys.argv:
        return  # It's not dev
    import json
    from pathlib import Path
    json_def = json.dumps(app.openapi(),
                          ensure_ascii=False,
                          allow_nan=False,
                          indent=None,
                          separators=(",", ":"))
    # Copy here for Git commit but also into another dev tree
    parent_dir = dirname(main_path)
    dests = [Path(parent_dir, "..", "openapi.json"),
             Path(parent_dir, "..", "..", "ecotaxa_master", "to_back/openapi.json")]
    for dest in dests:
        with dest.open("w") as fd:
            fd.write(json_def)


secured_scheme = HTTPBearer()

# Read from legacy app config
SECRET_KEY = read_config()['SECRET_KEY'][1:-1]
# Hardcoded in Flask
SALT = b"cookie-session"

serializer = URLSafeTimedSerializer(secret_key=SECRET_KEY, salt=SALT,
                                    signer=TimestampSigner, signer_kwargs={'key_derivation': 'hmac'})
max_age = 2678400  # max token age, 31 days


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(secured_scheme)) -> int:
    """
        Extract current user from auth string.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if creds.scheme != 'Bearer':
            raise credentials_exception
        payload = serializer.loads(creds.credentials, max_age=max_age)
        try:
            ret: int = int(payload["user_id"])
        except (KeyError, ValueError):
            raise credentials_exception
    except (SignatureExpired, BadSignature):
        raise credentials_exception
    if ret < 0:
        raise credentials_exception
    return ret
