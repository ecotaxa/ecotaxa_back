import pytest
from starlette import status

from tests.credentials import ADMIN_AUTH
from tests.test_classification import get_stats
from tests.test_import import do_test_import
from tests.test_reclassification import detritus_classif_id, reclassify

SEARCH_WORMS_URL = "/searchworms/{}"
TAXA_FROM_CENTRAL_URL = "/taxa/pull_from_central"
TAXON_PUT = "/taxon/central"

ACARTIA_RSP = [
    {
        "aphia_id": 104108,
        "name": "Acartia",
        "rank": "Genus",
        "status": "accepted",
        "lineage": {
            "104108": {
                "AphiaID": 104074,
                "rank": "Family",
                "scientificname": "Acartiidae",
            },
            "104074": {"AphiaID": 1100, "rank": "Order", "scientificname": "Calanoida"},
            "1100": {
                "AphiaID": 155877,
                "rank": "Superorder",
                "scientificname": "Gymnoplea",
            },
            "155877": {
                "AphiaID": 155876,
                "rank": "Infraclass",
                "scientificname": "Neocopepoda",
            },
            "155876": {"AphiaID": 1080, "rank": "Class", "scientificname": "Copepoda"},
            "1080": {
                "AphiaID": 845959,
                "rank": "Superclass",
                "scientificname": "Multicrustacea",
            },
            "845959": {
                "AphiaID": 1066,
                "rank": "Subphylum",
                "scientificname": "Crustacea",
            },
            "1066": {"AphiaID": 1065, "rank": "Phylum", "scientificname": "Arthropoda"},
            "1065": {"AphiaID": 2, "rank": "Kingdom", "scientificname": "Animalia"},
            "2": {"AphiaID": 1, "rank": "Superdomain", "scientificname": "Biota"},
        },
        "id": 80116,
    }
]


def test_search_worms_name(fastapi, mocker):
    # Mock the 'call' method of EcoTaxoServerClient
    mock_call = mocker.patch("providers.EcoTaxoServer.EcoTaxoServerClient.call")
    mock_response = mocker.Mock()
    mock_response.json.return_value = ACARTIA_RSP
    mock_call.return_value = mock_response

    url = SEARCH_WORMS_URL.format("Acartia")
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == ACARTIA_RSP

    # Verify the mock was called correctly
    mock_call.assert_called_with("/wormstaxon/Acartia", {}, "get")


def test_pull_taxa_update_from_central(fastapi, mocker):
    prj_id = do_test_import(fastapi, "TSV deprecated export project")

    # Mock the 'call' method of EcoTaxoServerClient
    mock_call = mocker.patch("providers.EcoTaxoServer.EcoTaxoServerClient.call")
    fake_taxon = {
        "id": 999999,
        "parent_id": 1,
        "name": "TestTaxon",
        "taxotype": "P",
        "taxostatus": "N",
        "aphia_id": 123456,
        "rank": "Species",
        "id_instance": 1,
        "rename_to": None,
        "display_name": "TestTaxon",
        "source_desc": "Test source",
        "source_url": "http://test.com",
        "creation_datetime": "2021-08-20 09:09:39",
        "creator_email": "test@test.com",
        "lastupdate_datetime": "2021-08-20 09:09:40",
    }
    mock_updates = [fake_taxon]

    mock_response = mocker.Mock()
    mock_response.json.return_value = mock_updates
    mock_call.return_value = mock_response

    rsp = fastapi.get(TAXA_FROM_CENTRAL_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == {"inserts": 1, "updates": 0, "error": None}

    # Reclassify all detritus in the loaded project to imported taxon 999999
    reclassify(fastapi, prj_id, detritus_classif_id, 999999)
    # Verify reclassification
    stats = get_stats(fastapi, prj_id)
    assert 999999 in stats["used_taxa"]
    assert detritus_classif_id not in stats["used_taxa"]

    rsp = fastapi.get(TAXA_FROM_CENTRAL_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == {"inserts": 0, "updates": 0, "error": None}

    fake_taxon["creator_email"] = "me@mysite.org"
    rsp = fastapi.get(TAXA_FROM_CENTRAL_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == {"inserts": 0, "updates": 0, "error": None}

    fake_taxon["taxostatus"] = "X"
    with pytest.raises(Exception):
        # TODO: The triggers trick is NOK
        rsp = fastapi.get(TAXA_FROM_CENTRAL_URL, headers=ADMIN_AUTH)
        # assert rsp.status_code == status.HTTP_200_OK
        assert rsp.json() == {"inserts": 0, "updates": 0, "error": None}


def test_add_taxon_in_central(fastapi, mocker):
    # Mock the 'call' method of EcoTaxoServerClient
    mock_call = mocker.patch("providers.EcoTaxoServer.EcoTaxoServerClient.call")
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"msg": "ok", "id": 789999}
    mock_call.return_value = mock_response

    params = {
        "name": "NewTaxon",
        "parent_id": 1,
        "taxotype": "P",
        "creator_email": "creator@test.com",
        "source_desc": "Test source",
        "source_url": "http://test.com",
    }

    rsp = fastapi.put(TAXON_PUT, params=params, headers=ADMIN_AUTH)

    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json()["msg"] == "ok"

    # Verify the mock was called correctly
    # The service adds 'creation_datetime' and 'taxostatus'
    called_args = mock_call.call_args
    assert called_args[0][0] == "/settaxon/"
    sent_params = called_args[0][1]
    assert sent_params["name"] == "NewTaxon"
    assert (
        sent_params["parent_id"] == "1"
    )  # FastAPI Query params are strings in request.query_params
    assert sent_params["taxotype"] == "P"
    assert sent_params["creator_email"] == "creator@test.com"
    assert sent_params["taxostatus"] == "N"
    assert "creation_datetime" in sent_params


def test_add_taxon_in_central_unauthorized(fastapi, mocker):
    # Mock the 'call' method of EcoTaxoServerClient
    mock_call = mocker.patch("providers.EcoTaxoServer.EcoTaxoServerClient.call")

    params = {
        "name": "NewTaxonUnauthorized",
        "parent_id": 1,
        "taxotype": "P",
        "creator_email": "creator@test.com",
    }

    # Unauthenticated call
    rsp = fastapi.put(TAXON_PUT, params=params)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    assert mock_call.call_count == 0
