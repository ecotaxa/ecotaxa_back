from fastapi import status

from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import create_project, do_import_uvp6

PATCH_URL = "/projects/{project_id}"


def _admin_min_user(fastapi, prj_id):
    # The project already has the admin as contact/manager from creation,
    # so its embedded MinUserModel representation can be reused as-is.
    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    prj_json = fastapi.get(get_url, headers=ADMIN_AUTH).json()
    return prj_json["contact"]


def test_patch_project_empty_body(fastapi):
    # No field is required: an empty patch is a valid no-op.
    # A bare project (no import) is enough, no need for actual data.
    prj_id = create_project(ADMIN_USER_ID, "Patch Test Project Empty")
    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    before = fastapi.get(get_url, headers=ADMIN_AUTH).json()

    url = PATCH_URL.format(project_id=prj_id)
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text

    after = fastapi.get(get_url, headers=ADMIN_AUTH).json()
    assert before == after


def test_patch_project_title_only(fastapi):
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test Project")
    url = PATCH_URL.format(project_id=prj_id)
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"title": "Patched Title"})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text

    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(get_url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    assert prj_json["title"] == "Patched Title"
    # Untouched fields must be unaffected
    assert prj_json["status"] == "Annotate"


def test_patch_project_managers_without_contact(fastapi):
    # Reproduces the former NameError: patching managers/annotators/viewers
    # without also patching 'contact' in the same request.
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test Project Managers")
    url = PATCH_URL.format(project_id=prj_id)
    body = {"managers": [_admin_min_user(fastapi, prj_id)]}
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json=body)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text

    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(get_url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    assert len(prj_json["managers"]) == 1
    assert prj_json["managers"][0]["id"] == ADMIN_USER_ID


def test_patch_project_contact_and_managers(fastapi):
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test Project Contact")
    url = PATCH_URL.format(project_id=prj_id)
    admin_user = _admin_min_user(fastapi, prj_id)
    body = {"managers": [admin_user], "contact": admin_user}
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json=body)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text

    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(get_url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    assert prj_json["contact"]["id"] == ADMIN_USER_ID
    assert prj_json["managers"][0]["id"] == ADMIN_USER_ID
