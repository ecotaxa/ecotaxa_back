# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from starlette import status

from API_models.constants import Constants, FORMULAE
from BO.DataLicense import AccessLevelEnum


def test_used_constants(fastapi):
    response = fastapi.get("/constants")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["app_manager"] == ["Sam One", "someone@somewhere.org"]
    assert data["account_validation"] is False
    assert data["email_verification"] is False
    assert data["recaptchaid"] is False
    assert data["formulae"] == FORMULAE
    assert data["default_project_access"] == AccessLevelEnum.PUBLIC
    assert data["max_upload_size"] == 681574400
    assert data["time_to_live"] == "10"
    assert data["all_in_one"] is False
    assert data["taxoserver_url"] == "http://ecotaxoserver.dev.com/"
    assert data["openid_configured"] is True
    assert data["accepted_mime_types"] == [
        "application/zip",
        "application/gzip",
        "application/x-tar",
        "text/plain",
        "text/csv",
        "text/tab-separated-values",
        "image/jpeg",
        "image/png",
        "image/x-png",
        "image/gif",
        "image/tiff",
    ]
    assert data["archive_extensions"] == [
        "zip",
        "tar",
        "gzip",
        "tar.gz",
        "tar.bz2",
        "tar.xz",
        "gz",
    ]
    assert data["short_token_age"] == 1
    assert data["profile_token_age"] == 24
    assert (
        data["password_regexp"]
        == "^(?:(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#?%^&+*-])).{8,64}$"
    )
    assert data["access"] == {"PUBLIC": "1", "OPEN": "2", "PRIVATE": "0"}
    assert data["people_organization_directories"] == {
        "edmo": "https://edmo.seadatanet.org/",
        "orcid": "https://orcid.org/",
    }
    assert data["user_status"] == {
        "blocked": -1,
        "inactive": 0,
        "active": 1,
        "pending": 2,
    }
    assert data["user_type"] == {"guest": "guest", "user": "user"}
    assert data["recast_operation"] == {
        "prediction_input": "pre_predict",
        "prediction_output": "post_predict",
        "dwca_export_occurrence": "dwca_export_occurrence",
        "dwca_export_emof": "dwca_export_emof",
        "project_export": "project_export",
        "project_import": "project_import",
        "collection_export": "collection_export",
    }
    assert "France" in data["countries"]
    assert len(data["countries"]) > 200
    assert "CC0 1.0" in data["license_texts"]
    assert "CC BY 4.0" in data["license_texts"]
    assert "CC BY-NC 4.0" in data["license_texts"]
    assert "Copyright" in data["license_texts"]
    assert "" in data["license_texts"]
