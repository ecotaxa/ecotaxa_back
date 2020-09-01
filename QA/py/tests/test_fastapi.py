import logging

import pytest

from fastapi.testclient import TestClient
from fastapi import status
from tests.fastapi_fixture import fastapi_noauth
from tests.db_fixture import database

from main import app

client = TestClient(app)


def test_login(fastapi_noauth, database, caplog):
    caplog.set_level(logging.DEBUG)
    response = client.get("/login")
    # Post needed
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    response = client.post("/login", params={"username": "foo", "password": "bar"})
    # Params needed
    assert response.status_code == status.HTTP_200_OK


ADMIN_AUTH = {"Authorization": "Bearer 1"}


def test_users(fastapi_noauth, database):
    response = client.get("/users")
    # Check that we cannot do without auth
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = client.get("/users", headers=ADMIN_AUTH)
    # Check that we can do with auth
    assert response.status_code == status.HTTP_200_OK


def test_user_me(fastapi_noauth):
    response = client.get("/users/me")
    # Check that we cannot do without auth
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = client.get("/users/me", headers=ADMIN_AUTH)
    # Check that we can do with auth
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == 'Application Administrator'
