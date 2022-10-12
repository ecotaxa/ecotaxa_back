import logging

from fastapi.testclient import TestClient
from fastapi import status

from main import app

from tests.credentials import ADMIN_AUTH, USER_AUTH, CREATOR_AUTH, ADMIN_USER_ID, USER2_AUTH


def test_users(config, database, fastapi):
    url = "/users"
    response = fastapi.get(url)
    # Check that we cannot do without auth
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = fastapi.get(url, headers=ADMIN_AUTH)
    # Check that we can do with auth
    assert response.status_code == status.HTTP_200_OK


USER_ME_URL = "/users/me"


def test_user_me(config, database, fastapi):
    url = USER_ME_URL
    response = fastapi.get(url)
    # Check that we cannot do without auth
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = fastapi.get(url, headers=ADMIN_AUTH)
    # Check that we can do with auth
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == 'Application Administrator'


def test_create_project(config, database, fastapi, caplog):
    caplog.set_level(logging.DEBUG)
    url = "/projects/create"
    # Check that we cannot do without auth
    response = fastapi.post(url, json={"title": "Oh no"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    # Check that we cannot do as ordinary user
    response = fastapi.post(url, headers=USER_AUTH, json={"title": "Oh no again"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    # Check that we can do as admin
    response = fastapi.post(url, headers=ADMIN_AUTH, json={"title": "Oh yes"})
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()) > 0
    # Check that we can do as project creator
    response = fastapi.post(url, headers=CREATOR_AUTH, json={"title": "Oh yes again"})
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()) > 0


def test_clone_project(config, database, fastapi, caplog):
    caplog.set_level(logging.CRITICAL)
    from tests.test_import import test_import
    prj_id = test_import(config, database, caplog, "Clone source")
    caplog.set_level(logging.DEBUG)
    url = "/projects/create"
    # Failing attempt
    response = fastapi.post(url, headers=ADMIN_AUTH, json={"title": "Clone of 1", "clone_of_id": -1})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # Working attempt
    response = fastapi.post(url, headers=ADMIN_AUTH, json={"title": "Clone of 1", "clone_of_id": prj_id})
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()) > 0
    # TODO: Check that the clone works
    # TODO: a nice diff


PROJECT_QUERY_URL = "/projects/{project_id}?for_managing={manage}"


def test_query_project(config, database, fastapi, caplog):
    url = PROJECT_QUERY_URL.format(project_id=88888888, manage=True)
    response = fastapi.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = fastapi.get(url, headers=USER_AUTH)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # Even admin cannot see a project which doesn't exist
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_user_search(config, database, fastapi, caplog):
    url = "/users/search?by_name=%s"
    response = fastapi.get(url % "jo")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = fastapi.get(url % "%adm%", headers=USER_AUTH)
    assert response.status_code == status.HTTP_200_OK
    rsp = response.json()
    assert len(rsp) == 1


def test_user_get(config, database, fastapi, caplog):
    url = "/users/%d"
    response = fastapi.get(url % 1)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = fastapi.get(url % 1000000, headers=USER_AUTH)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = fastapi.get(url % ADMIN_USER_ID, headers=USER_AUTH)
    assert response.status_code == status.HTTP_200_OK
    rsp = response.json()
    assert rsp["name"] == "Application Administrator"


def test_project_search(config, database, fastapi):
    url = "/projects/search"
    # Ordinary user looking at own projects
    response = fastapi.get(url, headers=USER_AUTH, params={"also_others": False,
                                                           "title_filter": "laur",
                                                           "instrument_filter": "flow"})
    assert response.json() == []
    # Ordinary user looking at all projects by curiosity
    response = fastapi.get(url, headers=USER_AUTH, params={"also_others": True,
                                                           "title_filter": "laur",
                                                           "instrument_filter": "flow"})
    assert response.json() == []
    # Creator user looking at his subsets for removing them
    response = fastapi.get(url, headers=CREATOR_AUTH, params={"also_others": False,
                                                              "title_filter": "tara",
                                                              "instrument_filter": "flow",
                                                              "filter_subset": True,
                                                              "for_managing": True})
    # TODO: Windowing tests
    assert response.json() == []


def test_error(fastapi):
    # We need a test client which does not catch exceptions
    client = TestClient(app, raise_server_exceptions=False)
    url = "/error"
    response = client.get(url, headers=USER_AUTH)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # Check that our line is present
    assert "--- BACK-END ---" in response.content.decode("utf-8")


def test_status(config, database, fastapi):
    # We need a test client which does not catch exceptions
    url = "/status"
    response = fastapi.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.text == "UP!"
    response = fastapi.get(url, headers=USER_AUTH)
    assert response.status_code == status.HTTP_200_OK
    # Random check of one entry
    assert "somepath" in response.content.decode("utf-8")
    response = fastapi.get(url, headers=ADMIN_AUTH)
    assert response.status_code == status.HTTP_200_OK
    # Random check of an admin entry
    assert "FTPEXPORTAREA" in response.content.decode("utf-8")


PRJ_CREATE_URL = "/projects/create"


def test_user_prefs(config, database, fastapi, caplog):
    # Create an empty project
    url1 = PRJ_CREATE_URL
    response = fastapi.post(url1, headers=ADMIN_AUTH, json={"title": "Prefs test"})
    prj_id = response.json()
    # Play with prefs
    get_url = "/users/my_preferences/%d?key=%s"
    response = fastapi.get(get_url % (prj_id, "usr2"))
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = fastapi.get(get_url % (prj_id, "usr2"), headers=USER2_AUTH)
    assert response.json() == ""
    put_url = "/users/my_preferences/%d?key=%s&value=%s"
    response = fastapi.put(put_url % (prj_id, "usr2", "value456"), headers=USER2_AUTH)
    assert response.json() is None
    response = fastapi.get(get_url % (prj_id, "usr2"), headers=USER2_AUTH)
    assert response.json() == "value456"
    erase_url = "/users/my_preferences/%d?key=%s&value="
    response = fastapi.put(erase_url % (prj_id, "usr2"), headers=USER2_AUTH)
    assert response.json() is None
    response = fastapi.get(get_url % (prj_id, "usr2"), headers=USER2_AUTH)
    assert response.json() == ""
