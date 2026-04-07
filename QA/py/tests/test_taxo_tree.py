#
# Tests about the taxonomy tree, globally.
#
import logging

from starlette import status

from tests.credentials import USER_AUTH

TREE_STATUS_URL = "/taxa/status"


def test_taxotree_status(fastapi):
    """This depends on the DB which has a subset of the production one"""

    url = TREE_STATUS_URL
    # Unauthenticated call
    rsp = fastapi.get(url)
    # Security barrier. No special right but we need a registered user.
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Authenticated call
    rsp = fastapi.get(url, headers=USER_AUTH)
    # Security barrier. No special right but we need a registered user.
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == {"last_refresh": None}

    # Second authenticated call, as the _only_ line in DB table should exist now
    rsp = fastapi.get(url, headers=USER_AUTH)
    # Security barrier. No special right but we need a registered user.
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == {"last_refresh": None}
