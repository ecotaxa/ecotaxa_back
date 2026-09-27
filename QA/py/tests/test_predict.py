import pytest
from starlette import status

from tests.api_wrappers import JOB_QUERY_URL, JOB_DELETE_URL
from tests.credentials import (
    ADMIN_AUTH,
    ADMIN_USER_ID,
    CREATOR_AUTH,
    CREATOR_USER_ID,
    ORDINARY_USER_USER_ID,
    USER_AUTH,
)
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import do_test_import, create_project
from tests.test_update_prj import PROJECT_UPDATE_URL

OBJECT_SET_PREDICT_URL = "/object_set/predict"


def test_predict_unauthenticated(fastapi):
    """
    Unauthenticated call to /object_set/predict should return 403 Forbidden.
    """
    payload = {
        "filters": {},
        "request": {
            "project_id": 1,
            "source_project_ids": [1],
            "features": ["area", "mean"],
            "categories": [25828],
            "pre_mapping": {},
        },
    }
    rsp = fastapi.post(OBJECT_SET_PREDICT_URL, json=payload)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN


def test_predict_not_authorized(fastapi):
    """
    User without annotate rights on the project should receive 403 Forbidden.
    """
    prj_id = do_test_import(fastapi, "Predict Auth Test Project")

    payload = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "source_project_ids": [prj_id],
            "features": ["area", "mean"],
            "categories": [25828],
            "pre_mapping": {},
        },
    }
    rsp = fastapi.post(OBJECT_SET_PREDICT_URL, headers=USER_AUTH, json=payload)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN


def test_predict_project_not_found(fastapi):
    """
    Calling /object_set/predict for a non-existent project should return 404 Not Found.
    """
    payload = {
        "filters": {},
        "request": {
            "project_id": 9999999,
            "source_project_ids": [9999999],
            "features": ["area", "mean"],
            "categories": [25828],
            "pre_mapping": {},
        },
    }
    rsp = fastapi.post(OBJECT_SET_PREDICT_URL, headers=ADMIN_AUTH, json=payload)
    assert rsp.status_code == status.HTTP_404_NOT_FOUND


def test_predict_validation_errors(fastapi):
    """
    Invalid payloads (e.g. missing required fields or empty lists) should return 422 Unprocessable Content.
    """
    prj_id = do_test_import(fastapi, "Predict Validation Test Project")

    # Missing request field
    rsp = fastapi.post(
        OBJECT_SET_PREDICT_URL,
        headers=ADMIN_AUTH,
        json={"filters": {}},
    )
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Missing features
    rsp = fastapi.post(
        OBJECT_SET_PREDICT_URL,
        headers=ADMIN_AUTH,
        json={
            "filters": {},
            "request": {
                "project_id": prj_id,
                "source_project_ids": [prj_id],
                "features": [],
                "categories": [25828],
                "pre_mapping": {},
            },
        },
    )
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Missing source_project_ids
    rsp = fastapi.post(
        OBJECT_SET_PREDICT_URL,
        headers=ADMIN_AUTH,
        json={
            "filters": {},
            "request": {
                "project_id": prj_id,
                "source_project_ids": [],
                "features": ["area"],
                "categories": [25828],
                "pre_mapping": {},
            },
        },
    )
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_predict_success_admin(fastapi):
    """
    Admin successfully initiates a prediction job on an imported project.
    """
    prj_id = do_test_import(fastapi, "Predict Admin Test Project")

    payload = {
        "filters": {
            "taxo": "25828",
            "statusfilter": "NV",
        },
        "request": {
            "project_id": prj_id,
            "source_project_ids": [prj_id],
            "learning_limit": 50,
            "features": ["area", "mean", "major", "minor"],
            "categories": [25828, 25835],
            "use_scn": True,
            "pre_mapping": {25835: 25828},
        },
    }
    rsp = fastapi.post(OBJECT_SET_PREDICT_URL, headers=ADMIN_AUTH, json=payload)
    assert rsp.status_code == status.HTTP_200_OK

    data = rsp.json()
    assert "job_id" in data
    assert data["job_id"] > 0
    assert data["errors"] == []
    assert data["warnings"] == []

    # Verify that the job was properly registered in the database
    job_id = data["job_id"]
    try:
        job_url = JOB_QUERY_URL.format(job_id=job_id)
        job_rsp = fastapi.get(job_url, headers=ADMIN_AUTH)
        assert job_rsp.status_code == status.HTTP_200_OK

        job_data = job_rsp.json()
        assert job_data["id"] == job_id
        assert job_data["type"] == "Prediction"
        assert job_data["owner_id"] == ADMIN_USER_ID
        assert job_data["state"] == "P"  # Pending

        # Check job arguments
        params = job_data["params"]
        assert params["req"]["project_id"] == prj_id
        assert params["req"]["source_project_ids"] == [prj_id]
        assert params["req"]["learning_limit"] == 50
        assert params["req"]["features"] == ["area", "mean", "major", "minor"]
        assert params["req"]["categories"] == [25828, 25835]
        assert params["req"]["use_scn"] is True
        assert params["req"]["pre_mapping"] == {"25835": 25828}
        assert params["filters"]["taxo"] == "25828"
        assert params["filters"]["statusfilter"] == "NV"
    finally:
        del_rsp = fastapi.delete(
            JOB_DELETE_URL.format(job_id=job_id), headers=ADMIN_AUTH
        )
        assert del_rsp.status_code == status.HTTP_200_OK


def test_predict_annotator_privilege(fastapi):
    """
    A non-admin user granted 'Annotate' privilege on the project should be allowed to predict.
    """
    prj_id = do_test_import(fastapi, "Predict Annotator Test Project")

    # Grant annotator right to ORDINARY_USER_USER_ID
    qry_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(qry_url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    read_json = rsp.json()
    usr = {
        "id": ORDINARY_USER_USER_ID,
        "email": "ignored",
        "name": "see email",
        "organisation": "OrgTest",
    }
    read_json["annotators"].append(usr)
    upd_url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(upd_url, headers=ADMIN_AUTH, json=read_json)
    assert rsp.status_code == status.HTTP_200_OK

    payload = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "source_project_ids": [prj_id],
            "features": ["area"],
            "categories": [25828],
            "pre_mapping": {},
        },
    }
    rsp = fastapi.post(OBJECT_SET_PREDICT_URL, headers=USER_AUTH, json=payload)
    assert rsp.status_code == status.HTTP_200_OK
    data = rsp.json()
    assert data["job_id"] > 0

    job_id = data["job_id"]
    try:
        job_url = JOB_QUERY_URL.format(job_id=job_id)
        job_rsp = fastapi.get(job_url, headers=USER_AUTH)
        assert job_rsp.status_code == status.HTTP_200_OK
        job_data = job_rsp.json()
        assert job_data["id"] == job_id
        assert job_data["type"] == "Prediction"
        assert job_data["owner_id"] == ORDINARY_USER_USER_ID
    finally:
        del_rsp = fastapi.delete(
            JOB_DELETE_URL.format(job_id=job_id), headers=USER_AUTH
        )
        assert del_rsp.status_code == status.HTTP_200_OK


def test_predict_viewer_privilege_denied(fastapi):
    """
    A non-admin user granted only 'View' privilege on the project should NOT be allowed to predict (403).
    """
    prj_id = do_test_import(fastapi, "Predict Viewer Test Project")

    # Grant only viewer right to ORDINARY_USER_USER_ID
    qry_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(qry_url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    read_json = rsp.json()
    usr = {
        "id": ORDINARY_USER_USER_ID,
        "email": "ignored",
        "name": "see email",
        "organisation": "OrgTest",
    }
    read_json["viewers"] = [usr]
    upd_url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(upd_url, headers=ADMIN_AUTH, json=read_json)
    assert rsp.status_code == status.HTTP_200_OK

    payload = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "source_project_ids": [prj_id],
            "features": ["area"],
            "categories": [25828],
            "pre_mapping": {},
        },
    }
    rsp = fastapi.post(OBJECT_SET_PREDICT_URL, headers=USER_AUTH, json=payload)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
