# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, HTTPException
from starlette.responses import RedirectResponse

from API_models.crud import UserModelWithRights
from API_operations.CRUD.Users import UserService, OpenIDAccountConflict
from DB.User import UserStatus
from helpers.AppConfig import Config
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import issue_access_token
from helpers.httpexception import (
    DETAIL_OPENID_NOT_CONFIGURED,
    DETAIL_OPENID_PROVIDER_ERROR,
    DETAIL_OPENID_NO_USER_INFO,
    DETAIL_OPENID_EMAIL_NOT_VERIFIED,
)

oauth = OAuth()

router = APIRouter(
    prefix="/openid",
    tags=["openid"],
)

THE_PROVIDER = "gaia_data"

# The front reads these one-shot credentials from the callback response, server
# side, and keeps them in its own session. They are never relayed as browser
# cookies, so a cross-site script or a browser extension cannot steal them.
FRONT_TOKEN_HEADER = "X-Ecotaxa-Token"
FRONT_ID_TOKEN_HEADER = "X-Ecotaxa-Id-Token"

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
    # After a failed attempt, ask the provider to ignore its SSO session so
    # another account can be used. The front sets force_login for one attempt.
    force_login = request.query_params.get("force_login") == "1"
    try:
        if force_login:
            return await provider.authorize_redirect(
                request, redirect_uri, prompt="login"
            )
        return await provider.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"OpenID login redirect error: {e}")
        raise HTTPException(
            status_code=502, detail=[DETAIL_OPENID_PROVIDER_ERROR, str(e)]
        )


def _claim_text(value: Any) -> Optional[str]:
    """
    Return a usable string from a claim value.

    Most claims are plain strings, but Keycloak can send an object for the
    organization membership, for example {"my-org": {"name": "My Org"}}.
    """
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, dict):
        for key in ("name", "alias", "displayName"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for candidate in value.values():
            if isinstance(candidate, dict):
                name = candidate.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
    return None


def _first_claim(*values: Any) -> Optional[str]:
    for value in values:
        text = _claim_text(value)
        if text is not None:
            return text
    return None


def normalize_user_info(user_info: Dict[str, Any]) -> Dict[str, str]:
    """
    Map provider claims to the fields of a new EcoTaxa user.

    The "earth-data" claim is provider-specific and carries the organisation
    and country of the user. Top-level claims are kept as a fallback for
    providers which expose them directly.
    """
    earth_data = user_info.get("earth-data")
    if not isinstance(earth_data, dict):
        earth_data = {}

    email = _claim_text(user_info.get("email")) or ""
    name = _claim_text(user_info.get("name"))
    if name is None:
        given_name = _claim_text(user_info.get("given_name"))
        family_name = _claim_text(user_info.get("family_name"))
        name = " ".join(
            part for part in (given_name, family_name) if part is not None
        ) or None
    if name is None:
        name = email

    organisation = _first_claim(
        earth_data.get("organization"),
        earth_data.get("organisation"),
        user_info.get("organization"),
        user_info.get("organisation"),
    )
    country = _first_claim(
        earth_data.get("country"),
        user_info.get("country"),
    )
    orcid = _first_claim(
        user_info.get("orcid"),
        earth_data.get("orcid"),
    )
    return {
        "email": email,
        "name": name,
        "organisation": organisation or "Unknown",
        "country": country or "Unknown",
        "orcid": orcid or "",
        "usercreationreason": "Please fill in",
    }


def _email_is_verified(user_info: Dict) -> bool:
    """
    True only when the provider explicitly marks the email as verified.
    Some providers send the claim as a string, hence the normalisation.
    """
    val = user_info.get("email_verified")
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return False


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
        logger.error("OpenID callback access token error: %s", e)
        raise HTTPException(
            status_code=502, detail=[DETAIL_OPENID_PROVIDER_ERROR, str(e)]
        )

    user_info = token.get("userinfo")
    subject = user_info.get("sub") if user_info is not None else None
    raw_email = user_info.get("email") if user_info is not None else None
    if not subject or not raw_email:
        logger.warning("OpenID callback: missing sub or email in user info")
        raise HTTPException(status_code=400, detail=[DETAIL_OPENID_NO_USER_INFO])
    email = str(raw_email).strip()

    if Config().get_openid_require_verified_email() and not _email_is_verified(
        user_info
    ):
        logger.warning("OpenID login refused: email not verified by the provider")
        raise HTTPException(status_code=403, detail=[DETAIL_OPENID_EMAIL_NOT_VERIFIED])

    # Stable provider identity. "iss" comes from the validated ID token; the
    # configured metadata URL is an offline fallback if it is missing.
    _, _, metadata_url = Config().get_openid_config()
    issuer = str(user_info.get("iss") or metadata_url)

    id_token = token.get("id_token")
    norm_info = normalize_user_info(user_info)
    # Fill missing UserModelWithRights fields with relevant data
    new_user = UserModelWithRights(
        id=-1,
        email=email,
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

    with UserService() as sce:
        try:
            db_user = sce.add_openid_user(
                new_user=new_user, issuer=issuer, subject=subject
            )
        except OpenIDAccountConflict as e:
            # issuer/subject identify the refused login without logging PII
            logger.warning(
                "OpenID login refused for identity %s/%s: %s",
                issuer,
                subject,
                e.detail,
            )
            raise HTTPException(status_code=e.status_code, detail=[e.detail])
        # A blocked, inactive or not-yet-validated account must not get a token,
        # even when the provider authenticates it fine.
        if db_user.status != UserStatus.active.value:
            logger.warning(
                "OpenID login refused for non-active user %d (status %s)",
                db_user.id,
                db_user.status,
            )
            raise HTTPException(
                status_code=403,
                detail=[UserService.openid_account_status_detail(db_user.status)],
            )
        user_id = db_user.id

    logger.info("OpenID login for user %d", user_id)
    front_url = Config().get_account_validation_url()
    response = RedirectResponse(url=front_url)
    # The response carries credentials in its headers, never let a proxy cache it.
    response.headers["Cache-Control"] = "no-store"
    # The front calls /users/me with this token, then discards it. A short-lived
    # access token is enough, it does not need to be usable for 31 days.
    response.headers[FRONT_TOKEN_HEADER] = issue_access_token(user_id)
    if id_token:
        response.headers[FRONT_ID_TOKEN_HEADER] = id_token
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
    id_token_hint = request.headers.get(FRONT_ID_TOKEN_HEADER)
    if end_session_endpoint:
        params = {
            "post_logout_redirect_uri": front_url,
            "client_id": client_id,
        }
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        response = RedirectResponse(url=end_session_endpoint + "?" + urlencode(params))
    else:
        response = RedirectResponse(url=front_url)
    # The OIDC state cookie has no use once the user is logged out.
    response.delete_cookie("oid_session", path="/")
    return response
