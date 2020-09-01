import logging

from fastapi.testclient import TestClient
from fastapi import status

from main import app

client = TestClient(app)


def test_login(config, database, fastapi_noauth, caplog):
    caplog.set_level(logging.DEBUG)
    url = "/login"
    response = client.get(url)
    # Post needed
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    response = client.post(url, params={"username": "foo", "password": "bar"})
    # Params needed
    assert response.status_code == status.HTTP_200_OK


# These correspond to the rights in schema_prod.sql
ADMIN_AUTH = {"Authorization": "Bearer 1"}
USER_AUTH = {"Authorization": "Bearer 2"}
CREATOR_AUTH = {"Authorization": "Bearer 3"}


def test_users(config, database, fastapi_noauth):
    url = "/users"
    response = client.get(url)
    # Check that we cannot do without auth
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = client.get(url, headers=ADMIN_AUTH)
    # Check that we can do with auth
    assert response.status_code == status.HTTP_200_OK


def test_user_me(config, database, fastapi_noauth):
    url = "/users/me"
    response = client.get(url)
    # Check that we cannot do without auth
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = client.get(url, headers=ADMIN_AUTH)
    # Check that we can do with auth
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == 'Application Administrator'


def test_create_project(config, database, fastapi_noauth, caplog):
    caplog.set_level(logging.DEBUG)
    url = "/projects/create"
    # Check that we cannot do without auth
    response = client.post(url, json={"title": "Oh no"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    # Check that we cannot do as ordinary user
    response = client.post(url, headers=USER_AUTH, json={"title": "Oh no again"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    # Check that we can do as admin
    response = client.post(url, headers=ADMIN_AUTH, json={"title": "Oh yes"})
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()) > 0
    # Check that we can do as project creator
    response = client.post(url, headers=CREATOR_AUTH, json={"title": "Oh yes again"})
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()) > 0
