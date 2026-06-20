# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

from datetime import datetime
from typing import Dict
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth  # type:ignore
from fastapi import APIRouter, Request, HTTPException
from starlette.responses import RedirectResponse

from API_models.crud import UserModelWithRights
from API_operations.CRUD.Users import UserService
from helpers.AppConfig import Config
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import build_serializer
from helpers.httpexception import (
    DETAIL_OPENID_NOT_CONFIGURED,
    DETAIL_OPENID_PROVIDER_ERROR,
)

oauth = OAuth()

router = APIRouter(
    prefix="/openid",
    tags=["openid"],
)

THE_PROVIDER = "gaia_data"

logger = get_logger(__name__)


def init_openid():
    client_id, client_secret, server_metadata_url = Config().get_openid_config()

    if client_id is None:
        logger.info("OpenID provider NOT registered (missing config).")
        return
    # For self-signed local https in dev
    strict_verify = (
        False if server_metadata_url.startswith("https://localhost") else True
    )
    oauth.register(
        name=THE_PROVIDER,
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=server_metadata_url,
        client_kwargs={
            "scope": "openid email profile",
            "code_challenge_method": "S256",
            "verify": strict_verify,
        },
    )
    logger.info("OpenID provider registered.")


@router.get("/login", operation_id="openid_login")
async def openid_login(request: Request):
    """
    Initiate OpenID connection flow.
    """
    provider = getattr(oauth, THE_PROVIDER, None)
    if provider is None:
        raise HTTPException(status_code=503, detail=[DETAIL_OPENID_NOT_CONFIGURED])
    front_url = Config().get_account_validation_url()
    assert front_url is not None
    redirect_uri = front_url + "openid/callback"
    # If we are behind a proxy, we might need to force https
    if request.headers.get("x-forwarded-proto") == "https":
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    try:
        return await provider.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"OpenID login redirect error: {e}")
        raise HTTPException(
            status_code=502, detail=[DETAIL_OPENID_PROVIDER_ERROR, str(e)]
        )


def normalize_user_info(user_info: Dict[str, str]):
    email = user_info.get("email")
    name = user_info.get("name")
    if name is None:
        given_name = user_info.get("given_name")
        family_name = user_info.get("family_name")
        if given_name or family_name:
            name = (
                (given_name if given_name else "")
                + (" " if given_name and family_name else "")
                + (family_name if family_name else "")
            )
        else:
            name = email
    return {
        "email": email,
        "name": name,
        "organisation": user_info.get("organization", "Unknown"),
        "country": user_info.get("country", "Unknown"),
        "orcid": user_info.get("orcid", ""),
        "usercreationreason": "Please fill in",
    }


@router.get(
    "/callback",
    operation_id="openid_callback",
)
async def openid_callback(request: Request):
    """
    Handle OpenID provider callback.
    """
    provider = getattr(oauth, THE_PROVIDER, None)
    if provider is None:
        raise HTTPException(status_code=503, detail=[DETAIL_OPENID_NOT_CONFIGURED])
    try:
        token = await provider.authorize_access_token(request)
    except Exception as e:
        logger.error(f"OpenID callback access token error: {e}")
        raise HTTPException(
            status_code=502, detail=[DETAIL_OPENID_PROVIDER_ERROR, str(e)]
        )
    user_info = token.get("userinfo")
    logger.info("Callback got user_info %s", str(user_info))
    if user_info is None:
        return {
            "status": "error",
            "message": "OpenID authentication failed: no user_info",
        }
    email = user_info.get("email")
    if email is None:
        return {
            "status": "error",
            "message": "OpenID authentication failed: no email in user_info",
        }
    id_token = token.get("id_token")

    with UserService() as sce:
        _subject = user_info.get(
            "sub"
        )  # TODO: This one is unique, e.g. if user changes mail it will still point at him
        db_user = sce.find_by_email(email=email)
        if db_user is not None:
            # TODO: Anything to align here?
            # We could align name, organization, etc. if we wanted to trust OpenID provider more than our DB
            user_id = db_user.id
        else:
            # Self-register or convert
            norm_info = normalize_user_info(user_info)
            # Fill missing UserModelWithRights fields with relevant data
            new_user = UserModelWithRights(
                id=-1,
                email=norm_info["email"],
                mail_status=True,  # Trust provider
                mail_status_date=datetime.now(),
                status_date=datetime.now(),
                status_admin_comment="OpenID auto-registration",
                name=norm_info["name"],
                organisation=norm_info["organisation"],
                country=norm_info["country"],
                usercreationreason=norm_info["usercreationreason"],
                orcid=norm_info["orcid"],
                usercreationdate=datetime.now(),
                password=None,
            )
            user_id = sce.add_openid_user(new_user=new_user)
            logger.info("Added %s as %d", str(new_user), user_id)

            if user_id == -1:
                return {
                    "status": "error",
                    "message": "OpenID authentication failed: could not create user",
                }

        # User exists or was just created, log in by setting session
        front_url = Config().get_account_validation_url()
        assert front_url is not None
        token_for_flask = build_serializer().dumps({"user_id": user_id})
        response = RedirectResponse(url=front_url)
        response.set_cookie(key="token", value=str(token_for_flask))
        response.set_cookie(key="id_token", value=id_token)
        # Note: The session contains both "oid_session" and our tokens
        return response


@router.get("/logout", operation_id="openid_logout")
async def openid_logout(request: Request):
    """
    Log out from OpenID and local session.
    Returns a redirect to openid provider, it will clear its cookies and force a fresh login next time.
    """
    provider = getattr(oauth, THE_PROVIDER, None)
    if provider is None:
        raise HTTPException(status_code=503, detail=[DETAIL_OPENID_NOT_CONFIGURED])
    client_id, _, _ = Config().get_openid_config()
    try:
        metadata = await provider.load_server_metadata()
    except Exception as e:
        logger.error(f"OpenID logout metadata error: {e}")
        raise HTTPException(
            status_code=502, detail=[DETAIL_OPENID_PROVIDER_ERROR, str(e)]
        )
    end_session_endpoint = metadata.get("end_session_endpoint")
    front_url = Config().get_account_validation_url()
    assert front_url is not None
    if end_session_endpoint:
        params = {
            "id_token_hint": request.cookies.get("id_token"),
            "post_logout_redirect_uri": front_url,
            "client_id": client_id,
        }
        return RedirectResponse(url=end_session_endpoint + "?" + urlencode(params))
    return RedirectResponse(url=front_url)
