from starlette import status
from tests.credentials import ADMIN_AUTH, USER_AUTH


def test_get_users_admins(fastapi):
    """
    Test /users/admins endpoint.
    It should be public (no auth).
    """
    # No auth
    rsp = fastapi.get("/users/admins")
    assert rsp.status_code == status.HTTP_200_OK
    admins = rsp.json()
    assert isinstance(admins, list)
    # Usually there is at least one admin
    assert len(admins) >= 1

    # Also works with auth
    rsp = fastapi.get("/users/admins", headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_200_OK


def test_get_admin_users(fastapi):
    """
    Test /users/user_admins endpoint.
    It should require authentication.
    """
    # No auth should fail
    rsp = fastapi.get("/users/user_admins")
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # With user auth
    rsp = fastapi.get("/users/user_admins", headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    user_admins = rsp.json()
    assert isinstance(user_admins, list)
    assert len(user_admins) >= 1

    # With admin auth
    rsp = fastapi.get("/users/user_admins", headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
