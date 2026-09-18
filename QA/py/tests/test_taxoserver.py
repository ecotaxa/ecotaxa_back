import pytest
from starlette import status

from API_operations.helpers.Service import Service
from DB.Taxonomy import Taxonomy, TaxonomyTreeInfo
from tests.api_wrappers import api_wait_for_stable_job, api_get_log_file
from tests.credentials import ADMIN_AUTH
from tests.jobs import check_job_ok
from tests.test_classification import get_stats
from tests.test_import import do_test_import
from tests.test_reclassification import detritus_classif_id, reclassify

SEARCH_WORMS_URL = "/searchworms/{}"
TAXA_FROM_CENTRAL_URL = "/taxa/pull_from_central"
TAXON_PUT = "/taxon/central"
NIGHTLY_URL = "/admin/nightly"

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


def test_search_worms_name(fastapi, mock_taxoserver):
    mock_taxoserver.custom_responses["/wormstaxon/Acartia"] = ACARTIA_RSP

    url = SEARCH_WORMS_URL.format("Acartia")
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == ACARTIA_RSP

    # Verify the mock was called correctly
    mock_taxoserver.mock_call.assert_called_with("/wormstaxon/Acartia", {}, "get")


def test_pull_taxa_update_from_central(fastapi, mock_taxoserver):
    prj_id = do_test_import(fastapi, "TSV deprecated export project")

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
    mock_taxoserver.taxa_updates = [fake_taxon]

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


def test_add_taxon_in_central(fastapi, mock_taxoserver):
    mock_taxoserver.settaxon_response = {"msg": "ok", "id": 789999}

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
    called_args = mock_taxoserver.mock_call.call_args
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


def test_add_taxon_in_central_unauthorized(fastapi, mock_taxoserver):
    params = {
        "name": "NewTaxonUnauthorized",
        "parent_id": 1,
        "taxotype": "P",
        "creator_email": "creator@test.com",
    }

    # Unauthenticated call
    rsp = fastapi.put(TAXON_PUT, params=params)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    assert mock_taxoserver.mock_call.call_count == 0


def test_nightly_job_central_taxonomy_sync(fastapi, mock_taxoserver):
    fake_taxon = {
        "id": 999888,
        "parent_id": 1,
        "name": "NightlyTaxon",
        "taxotype": "P",
        "taxostatus": "N",
        "aphia_id": 654321,
        "rank": "Species",
        "id_instance": 1,
        "rename_to": None,
        "display_name": "NightlyTaxon",
        "source_desc": "Nightly source",
        "source_url": "http://test.com",
        "creation_datetime": "2021-08-20 09:09:39",
        "creator_email": "test@test.com",
        "lastupdate_datetime": "2021-08-20 09:09:40",
    }
    mock_taxoserver.taxa_updates = [fake_taxon]

    # Trigger nightly job
    rsp = fastapi.get(NIGHTLY_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()
    job = api_wait_for_stable_job(fastapi, job_id)
    check_job_ok(job)

    log = api_get_log_file(fastapi, job.id)
    assert any("Starting pull of taxonomy updates from central" in line for line in log)
    assert any("Pull of taxonomy updates from central done" in line for line in log)
    assert any("Starting push of taxonomy stats to central" in line for line in log)
    assert any("Push of taxonomy stats to central done" in line for line in log)

    # Verify pulled taxon was inserted into DB
    with Service() as sce:
        taxon = sce.session.get(Taxonomy, 999888)
        assert taxon is not None
        assert taxon.name == "NightlyTaxon"
        assert taxon.aphia_id == 654321

        # Verify tree status was updated after push
        tree_info = sce.session.get(TaxonomyTreeInfo, 1)
        assert tree_info is not None
        assert tree_info.lastserverversioncheck_datetime is not None


def test_nightly_job_central_taxonomy_pull_error(fastapi, mock_taxoserver):
    mock_taxoserver.taxa_updates = {"msg": "TaxoServer error"}

    rsp = fastapi.get(NIGHTLY_URL, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()
    job = api_wait_for_stable_job(fastapi, job_id)
    check_job_ok(job)

    log = api_get_log_file(fastapi, job.id)
    assert any("Starting pull of taxonomy updates from central" in line for line in log)
    assert any(
        "Pull of taxonomy updates from central failed: TaxoServer error" in line
        for line in log
    )
    assert any("Starting push of taxonomy stats to central" in line for line in log)
    assert any("Push of taxonomy stats to central done" in line for line in log)
