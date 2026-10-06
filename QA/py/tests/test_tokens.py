# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Access + refresh tokens, /token entry points.
#
from datetime import timedelta

from starlette import status

from API_models.crud import UserModelWithRights
from API_operations.CRUD.Users import UserService
from API_operations.Tokens import RefreshTokenService, _now
from DB.User import User, UserStatus, UserRefreshToken
from helpers import fastApiUtils
from tests.credentials import ADMIN_USER_ID
from tests.test_fastapi import USER_ME_URL
from tests.test_login import client  # noqa: F401 (fixture)
from tests.test_users_with_validation import create_db_user

TOKEN_URL = "/token"
REFRESH_URL = "/token/refresh"
REVOKE_URL = "/token/revoke"

# Note: No fastapi fixture here, as it skips auth


def _login(client, username="administrator@email.test", password="ecotaxa"):
    return client.post(TOKEN_URL, data={"username": username, "password": password})


def _pair(client, **kwargs):
    rsp = _login(client, **kwargs)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    return rsp.json()


def _me(client, access_token):
    return client.get(USER_ME_URL, headers={"Authorization": "Bearer " + access_token})


def _refresh(client, refresh_token):
    return client.post(REFRESH_URL, json={"refresh_token": refresh_token})


def test_token_login(database, client):
    pair = _pair(client)
    assert set(pair.keys()) == {
        "access_token",
        "token_type",
        "expires_in",
        "refresh_token",
        "refresh_expires_in",
    }
    assert pair["token_type"] == "bearer"
    assert pair["expires_in"] == 3600
    assert pair["refresh_expires_in"] == 2678400
    # Wrong password and inactive account
    rsp = _login(client, password="wrong")
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    rsp = _login(client, username="old_admin", password="nimda_dlo")
    assert rsp.status_code == status.HTTP_403_FORBIDDEN


def test_access_token(database, client, monkeypatch):
    pair = _pair(client)
    rsp = _me(client, pair["access_token"])
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["id"] == ADMIN_USER_ID
    # Tampered
    rsp = _me(client, pair["access_token"][:-2] + "xx")
    assert rsp.status_code == status.HTTP_401_UNAUTHORIZED
    # A refresh token is not an access token
    rsp = _me(client, pair["refresh_token"])
    assert rsp.status_code == status.HTTP_401_UNAUTHORIZED
    # Expired
    monkeypatch.setattr(fastApiUtils, "access_ttl", lambda: -1)
    rsp = _me(client, pair["access_token"])
    assert rsp.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_rotation_and_reuse(database, client):
    pair_a = _pair(client)
    rsp = _refresh(client, pair_a["refresh_token"])
    assert rsp.status_code == status.HTTP_200_OK
    pair_b = rsp.json()
    assert pair_b["refresh_token"] != pair_a["refresh_token"]
    assert _me(client, pair_b["access_token"]).status_code == status.HTTP_200_OK
    # Reuse of A: whole family is revoked, so B is dead too
    rsp = _refresh(client, pair_a["refresh_token"])
    assert rsp.status_code == status.HTTP_401_UNAUTHORIZED
    rsp = _refresh(client, pair_b["refresh_token"])
    assert rsp.status_code == status.HTTP_401_UNAUTHORIZED
    # Garbage
    rsp = _refresh(client, "garbage")
    assert rsp.status_code == status.HTTP_401_UNAUTHORIZED


def test_revoke(database, client):
    pair = _pair(client)
    rsp = client.post(REVOKE_URL, json={"refresh_token": pair["refresh_token"]})
    assert rsp.status_code == status.HTTP_200_OK
    assert _refresh(client, pair["refresh_token"]).status_code == 401
    rsp = client.post(REVOKE_URL, json={"refresh_token": "garbage"})
    assert rsp.status_code == status.HTTP_200_OK


def test_only_hashes_stored(database, client):
    pair = _pair(client)
    with RefreshTokenService() as sce:
        nb = (
            sce.session.query(UserRefreshToken)
            .filter(UserRefreshToken.token_hash == pair["refresh_token"])
            .count()
        )
    assert nb == 0


def _update_user(user_id, **changes):
    with UserService() as sce:
        usr = sce.session.get(User, user_id)
        src = UserModelWithRights.model_validate(usr)
        for k, v in changes.items():
            setattr(src, k, v)
        sce._model_to_db(usr, src, [getattr(User, k) for k in changes])


def test_revoked_on_password_change_and_block(database, client):
    user_id = create_db_user(email="refresh_user@test.org", password="Password123!")
    creds = {"username": "refresh_user@test.org", "password": "Password123!"}
    pair = _pair(client, **creds)
    _update_user(user_id, password="Password456!")
    assert _refresh(client, pair["refresh_token"]).status_code == 401

    creds["password"] = "Password456!"
    pair = _pair(client, **creds)
    _update_user(user_id, status=UserStatus.blocked.value)
    with RefreshTokenService() as sce:
        nb_live = (
            sce.session.query(UserRefreshToken)
            .filter(UserRefreshToken.user_id == user_id)
            .filter(UserRefreshToken.revoked_at.is_(None))
            .count()
        )
    assert nb_live == 0
    assert _refresh(client, pair["refresh_token"]).status_code == 401


def test_legacy_tokens(database, client, monkeypatch):
    rsp = client.post(
        "/login", json={"username": "administrator@email.test", "password": "ecotaxa"}
    )
    legacy = rsp.json()
    assert _me(client, legacy).status_code == status.HTTP_200_OK
    flask_cookie = fastApiUtils.build_serializer().dumps({"_user_id": ADMIN_USER_ID})
    monkeypatch.setattr(fastApiUtils, "legacy_tokens_on", lambda: False)
    assert _me(client, legacy).status_code == status.HTTP_401_UNAUTHORIZED
    # The front session cookie still works
    client.cookies.set("session", flask_cookie)
    try:
        assert client.get(USER_ME_URL).status_code == status.HTTP_200_OK
    finally:
        client.cookies.clear()


def test_purge_expired(database, client):
    live = _pair(client)
    expired = _pair(client)
    old_revoked = _pair(client)
    with RefreshTokenService() as sce:
        rows = {
            r.token_hash: r
            for r in sce.session.query(UserRefreshToken).order_by(
                UserRefreshToken.id.desc()
            )[:3]
        }
        by_age = sorted(rows.values(), key=lambda r: r.id)
        by_age[1].expires_at = _now() - timedelta(seconds=1)
        by_age[2].revoked_at = _now() - timedelta(days=8)
        sce.session.commit()
        assert sce.purge_expired() >= 2
    assert _refresh(client, live["refresh_token"]).status_code == 200
    assert _refresh(client, expired["refresh_token"]).status_code == 401
    assert _refresh(client, old_revoked["refresh_token"]).status_code == 401
