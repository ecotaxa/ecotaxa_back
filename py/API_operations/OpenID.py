# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)

import logging
from urllib.parse import urlencode

# type: ignore
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, HTTPException
from starlette.responses import RedirectResponse

from API_operations.CRUD.Users import UserService
from helpers.AppConfig import Config
from helpers.fastApiUtils import build_serializer
from helpers.httpexception import DETAIL_OPENID_NOT_CONFIGURED

oauth = OAuth()

router = APIRouter(
    prefix="/openid",
    tags=["openid"],
)

THE_PROVIDER = "gaia_data"


def init_openid():
    client_id, client_secret, server_metadata_url = Config().get_openid_config()

    if client_id is None:
        logging.info("OpenID provider NOT registered (missing config).")
        return
    oauth.register(
        name=THE_PROVIDER,
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=server_metadata_url,
        client_kwargs={
            'scope': 'openid email profile', 'code_challenge_method': 'S256'
        }
    )
    logging.info("OpenID provider registered.")


@router.get("/login")
async def openid_login(request: Request):
    """
    Initiate OpenID connection flow.
    """
    provider = getattr(oauth, THE_PROVIDER, None)
    if provider is None:
        raise HTTPException(status_code=503, detail=[DETAIL_OPENID_NOT_CONFIGURED])
    redirect_uri = Config().get_account_request_url() + 'openid/callback'
    # If we are behind a proxy, we might need to force https
    if request.headers.get("x-forwarded-proto") == "https":
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await provider.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def openid_callback(request: Request):
    """
    Handle OpenID provider callback.
    """
    provider = getattr(oauth, THE_PROVIDER, None)
    if provider is None:
        raise HTTPException(status_code=503, detail=[DETAIL_OPENID_NOT_CONFIGURED])
    token = await provider.authorize_access_token(request)
    user_info = token.get('userinfo')
    if user_info is None:
        return {"status": "error", "message": "OpenID authentication failed: no user_info"}
    email = user_info.get('email')
    if email is None:
        return {"status": "error", "message": "OpenID authentication failed: no email in user_info"}
    id_token = token.get('id_token')

    with UserService() as sce:
        sub = user_info.get('sub')  # TODO: This one is unique, e.g. if user changes mail it will still point at him
        db_user = sce.find_by_email(email=email)
        if db_user is not None:
            # User exists, log in by setting session
            front_url = Config().get_account_request_url()
            token_for_flask = build_serializer().dumps({"user_id": db_user.id})
            response = RedirectResponse(url=front_url)
            response.set_cookie(key="token", value=token_for_flask)
            response.set_cookie(key="id_token", value=id_token)
            # Note: The session contains both "oid_session" and "token"
            return response
        else:
            # TODO: Self-register?
            pass


@router.get("/logout")
async def openid_logout(request: Request):
    """
    Log out from OpenID and local session.
    """
    provider = getattr(oauth, THE_PROVIDER, None)
    if provider is None:
        raise HTTPException(status_code=503, detail=[DETAIL_OPENID_NOT_CONFIGURED])
    client_id, _, _ = Config().get_openid_config()
    metadata = await provider.load_server_metadata()
    end_session_endpoint = metadata.get('end_session_endpoint')
    front_url = Config().get_account_request_url()
    if end_session_endpoint:
        params = {
            'id_token_hint': request.cookies.get('id_token'),
            'post_logout_redirect_uri': front_url,
            'client_id': client_id
        }
        return RedirectResponse(url=end_session_endpoint+"?"+urlencode(params))
    return RedirectResponse(url=front_url)

