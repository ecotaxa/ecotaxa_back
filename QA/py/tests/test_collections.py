import logging

# noinspection PyPackageRequirements
import pytest
from starlette import status

from tests.credentials import ADMIN_AUTH, USER_AUTH, CREATOR_AUTH
from tests.test_fastapi import PROJECT_QUERY_URL, USER_ME_URL
from tests.test_update_prj import PROJECT_UPDATE_URL

PROJECT_EXPORT_EMODNET_URL = "/export/darwin_core?dry_run=False"

COLLECTION_CREATE_URL = "/collections/create"
COLLECTION_QUERY_URL = "/collections/{collection_id}"
COLLECTION_SEARCH_URL = "/collections/search?title={title}"
COLLECTION_EXACT_QUERY_URL = "/collections/by_short_title?q={short_title}"
COLLECTION_UPDATE_URL = "/collections/{collection_id}"
COLLECTION_DELETE_URL = "/collections/{collection_id}"

INSTRUMENT_QUERY_URL = "/instruments/?project_ids={project_id}"


@pytest.mark.parametrize("who", [ADMIN_AUTH, CREATOR_AUTH])
def test_collection_lifecycle(database, fastapi, caplog, who):
    caplog.set_level(logging.FATAL)

    # Admin (always) imports the project
    from tests.test_import import test_import

    prj_id = test_import(
        database, caplog, "Collection project 1", instrument="Other scanner"
    )

    # Small instrument 'list' test
    url = INSTRUMENT_QUERY_URL.format(project_id=prj_id)
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == ["Other scanner"]

    # All instruments 'list' test
    url = INSTRUMENT_QUERY_URL.format(project_id="all")
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == [
        "?",
        "AMNIS",
        "CPICS",
        "CytoSense",
        "FastCam",
        "FlowCam",
        "IFCB",
        "ISIIS",
        "LISST-Holo",
        "Loki",
        "Other camera",
        "Other flowcytometer",
        "Other microscope",
        "Other scanner",
        "PlanktoScope",
        "Plankton Imager",
        "UVP5HD",
        "UVP5SD",
        "UVP5Z",
        "UVP6",
        "VPR",
        "ZooCam",
        "Zooscan",
        "eHFCM",
    ]

    regrant_if_needed(fastapi, prj_id, who)

    # And creates a collection with it
    url = COLLECTION_CREATE_URL
    rsp = fastapi.post(
        url,
        headers=who,
        json={"title": "Test collection", "project_ids": [prj_id]},
    )
    assert rsp.status_code == status.HTTP_200_OK
    coll_id = rsp.json()

    # Faulty re-read
    url = COLLECTION_QUERY_URL.format(collection_id=-1)
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Re-read
    url = COLLECTION_QUERY_URL.format(collection_id=coll_id)
    rsp = fastapi.get(url)
    # No admin, error
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    rsp = fastapi.get(url, headers=who)
    assert rsp.status_code == status.HTTP_200_OK
    the_coll = rsp.json()
    assert the_coll == {
        "abstract": None,
        "associate_organisations": [],
        "external_id": "?",
        "external_id_system": "?",
        "associate_users": [],
        "citation": None,
        "contact_user": None,
        "creator_organisations": [],
        "creator_users": [],
        "description": None,
        "id": coll_id,
        "license": "",
        "project_ids": [prj_id],
        "provider_user": None,
        "title": "Test collection",
        "short_title": None,
    }

    # Update the abstract
    url = COLLECTION_UPDATE_URL.format(collection_id=coll_id)
    the_coll[
        "abstract"
    ] = """
    A bit less abstract...
    """
    the_coll["short_title"] = "my-tiny-title"
    the_coll["associate_organisations"] = ["An org"]
    the_coll["creator_organisations"] = ["At least one (ONE)"]
    rsp = fastapi.put(url, headers=who, json=the_coll)
    assert rsp.status_code == status.HTTP_200_OK

    # Fail updating the project list
    url = COLLECTION_UPDATE_URL.format(collection_id=coll_id)
    the_coll["project_ids"] = [1, 5, 6]
    with pytest.raises(Exception):
        rsp = fastapi.put(url, headers=who, json=the_coll)

    # Search for it
    url = COLLECTION_SEARCH_URL.format(title="%coll%")
    rsp = fastapi.get(url, headers=who)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == [
        {
            "abstract": """
    A bit less abstract...
    """,
            "associate_organisations": ["An org"],
            "associate_users": [],
            "external_id": "?",
            "external_id_system": "?",
            "citation": None,
            "contact_user": None,
            "creator_organisations": ["At least one (ONE)"],
            "creator_users": [],
            "description": None,
            "id": coll_id,
            "license": "",
            "project_ids": [prj_id],
            "provider_user": None,
            "title": "Test collection",
            "short_title": "my-tiny-title",
        }
    ]

    # Search by short title
    url = COLLECTION_EXACT_QUERY_URL.format(short_title="my-tiny-title")
    rsp = fastapi.get(url, headers=who)
    assert rsp.status_code == status.HTTP_200_OK

    # Wrong search by short title
    url = COLLECTION_EXACT_QUERY_URL.format(short_title="my-absent-title")
    rsp = fastapi.get(url, headers=who)
    assert rsp.status_code == status.HTTP_404_NOT_FOUND

    # Empty search test
    url = COLLECTION_SEARCH_URL.format(title="coll%")
    rsp = fastapi.get(url, headers=who)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == []

    # Delete the collection
    url = COLLECTION_DELETE_URL.format(collection_id=coll_id)
    rsp = fastapi.delete(url, headers=who)
    assert rsp.status_code == status.HTTP_200_OK

    # Ensure it's gone
    url = COLLECTION_QUERY_URL.format(collection_id=coll_id)
    rsp = fastapi.get(url, headers=who)
    assert rsp.status_code == status.HTTP_404_NOT_FOUND


def regrant_if_needed(fastapi, prj_id, who):
    # Grant project to other user if relevant
    if who != ADMIN_AUTH:
        url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
        rsp = fastapi.get(url, headers=ADMIN_AUTH)
        prj_json = rsp.json()
        prj_json["managers"].append(fastapi.get(USER_ME_URL, headers=who).json())
        url = PROJECT_UPDATE_URL.format(project_id=prj_id)
        rsp = fastapi.put(url, headers=ADMIN_AUTH, json=prj_json)
        assert rsp.status_code == status.HTTP_200_OK
