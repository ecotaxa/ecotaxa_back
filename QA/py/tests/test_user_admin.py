import logging

from tests.credentials import ADMIN_AUTH, USER_AUTH, ORDINARY_USER_USER_ID

# noinspection PyPackageRequirements


USER_UPDATE_URL = "/users/{user_id}"

USER_GET_URL = "/users/{user_id}"


def test_user_update(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    url = USER_GET_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    read_json = rsp.json()
    ref_json = {'email': 'user',
                'id': 2,
                'name': 'Ordinary User'}
    assert read_json == ref_json

    # Self update
    url = USER_UPDATE_URL.format(user_id=ORDINARY_USER_USER_ID)
    rsp = fastapi.put(url, headers=USER_AUTH, json=read_json)

    assert rsp.status_code == 200
    # actual = rsp.json()
    # assert actual == expected
