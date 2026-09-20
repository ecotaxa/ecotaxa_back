import logging
from urllib.parse import quote_plus

from starlette import status

from tests.credentials import USER_AUTH
from tests.test_import import do_test_import

TAXA_SEARCH_URL = "/taxon_set/search?query={query}&project_id={project_id}"
TAXA_QUERY_URL = "/taxon/{taxon_id}"
TAXA_SET_QUERY_URL = "/taxon_set/query?ids={taxa_ids}"
WORMS_TAXA_QUERY_URL = "/worms/{aphia_id}"
WORMSIFICATION_TAXA_SET_URL = "/taxon_set/wormsification?ids={taxa_ids}"
ROOT_TAXA_URL = "/taxa"


def test_root_taxa(fastapi):
    url = ROOT_TAXA_URL
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    json = rsp.json()
    for a_taxon in json:
        a_taxon["nb_objects"] = 0  # Unpredictable
        a_taxon["nb_children_objects"] = 0  # Unpredictable
        a_taxon["children"].sort()
    json.sort(key=lambda a_taxon: a_taxon["id"])
    assert json == [
        {
            "aphia_id": 1,
            "children": [2, 3, 4, 6, 2367, 2371, 85011, 85183, 99999, 100002, 100059],
            "display_name": "Biota",
            "id": 1,
            "id_lineage": [1],
            "lineage": ["Biota"],
            "lineage_status": "A",
            "name": "Biota",
            "nb_children_objects": 0,
            "nb_objects": 0,
            "rank": "Superdomain",
            "renm_id": None,
            "status": "A",
            "type": "P",
        },
        {
            "aphia_id": None,
            "children": [85012, 85013, 85014, 85015, 85016],
            "display_name": "temporary<",
            "id": 84959,
            "id_lineage": [84959],
            "lineage": ["temporary"],
            "lineage_status": "A",
            "name": "temporary",
            "nb_children_objects": 0,
            "nb_objects": 0,
            "rank": None,
            "renm_id": None,
            "status": "A",
            "type": "M",
        },
        {
            "aphia_id": None,
            "children": [84962, 84963, 85008],
            "display_name": "not-living",
            "id": 84960,
            "id_lineage": [84960],
            "lineage": ["not-living"],
            "lineage_status": "A",
            "name": "not-living",
            "nb_children_objects": 0,
            "nb_objects": 0,
            "rank": None,
            "renm_id": None,
            "status": "A",
            "type": "M",
        },
    ]


def test_taxotree_query(fastapi):
    """This depends on the DB which has a subset of the production one"""

    prj_id = do_test_import(fastapi, "Test taxo search")

    url = TAXA_SEARCH_URL.format(project_id=prj_id, query="")
    # Unauthenticated call
    rsp = fastapi.get(url)
    # Security barrier
    assert rsp.status_code == status.HTTP_200_OK

    # url = TAXA_SEARCH_URL.format(project_id=prj_id, query=quote_plus("cyano<living"))
    # # Unauthenticated call
    # rsp = fastapi.get(url, json={})
    # assert rsp.json() == [{'id': 233, 'pr': 0, 'renm_id': None, 'text': 'Cyanobacteria<Bacteria'},
    #                       {'id': 849, 'pr': 0, 'renm_id': None, 'text': 'Cyanobacteria<Proteobacteria'},
    #                       {'id': 2396, 'pr': 0, 'renm_id': None, 'text': 'Cyanophora'},
    #                       {'id': 1680, 'pr': 0, 'renm_id': None, 'text': 'Cyanophyceae'},
    #                       {'id': 2395, 'pr': 0, 'renm_id': None, 'text': 'Cyanoptyche'}]

    url = TAXA_SEARCH_URL.format(project_id=prj_id, query=quote_plus(" cyano "))
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.json() == [
        {
            "aphia_id": None,
            "id": 4941,
            "pr": 0,
            "renm_id": None,
            "status": "A",
            "text": "Actinoalloteichus cyanogriseus",
        },
        {
            "aphia_id": 146537,
            "id": 233,
            "pr": 0,
            "renm_id": None,
            "status": "A",
            "text": "Cyanobacteria<Negibacteria",
        },
        {
            "aphia_id": None,
            "id": 849,
            "pr": 0,
            "renm_id": 233,
            "status": "D",
            "text": "Cyanobacteria<Proteobacteria",
        },
        {
            "aphia_id": None,
            "id": 2396,
            "pr": 0,
            "renm_id": None,
            "status": "A",
            "text": "Cyanophora",
        },
        {
            "aphia_id": 146542,
            "id": 1680,
            "pr": 0,
            "renm_id": None,
            "status": "A",
            "text": "Cyanophyceae",
        },
        {
            "aphia_id": None,
            "id": 2395,
            "pr": 0,
            "renm_id": None,
            "status": "A",
            "text": "Cyanoptyche",
        },
        {
            "aphia_id": None,
            "id": 3522,
            "pr": 0,
            "renm_id": None,
            "status": "A",
            "text": "Streptomyces cyanoalbus",
        },
    ]


def test_taxo_query(fastapi):
    """This depends on the DB which has a subset of the production one"""
    prj_id = do_test_import(fastapi, "Test taxo query")

    url = TAXA_QUERY_URL.format(taxon_id=849)
    # Unauthenticated call
    rsp = fastapi.get(url)
    # Security barrier
    assert rsp.status_code == status.HTTP_200_OK

    url = TAXA_QUERY_URL.format(taxon_id=849)
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.json() == {
        "children": [],
        "display_name": "Cyanobacteria<Proteobacteria",
        "id": 849,
        "lineage": ["Cyanobacteria", "Proteobacteria", "Bacteria", "Biota"],
        "id_lineage": [849, 96, 3, 1],
        "name": "Cyanobacteria",
        "nb_children_objects": 0,
        "nb_objects": 0,
        "renm_id": 233,
        "type": "P",
        "aphia_id": None,
        "lineage_status": "DAAA",
        "rank": None,
        "status": "D",
    }


def test_worms_query(fastapi):
    url = WORMS_TAXA_QUERY_URL.format(aphia_id=128586)
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.json() is None


def test_wormsification_taxa_set(fastapi):
    # 1. Unauthenticated call with multiple IDs (taxon 1 - Biota, taxon 233 - Cyanobacteria)
    url = WORMSIFICATION_TAXA_SET_URL.format(taxa_ids="1:233")
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    data = rsp.json()
    assert "1" in data
    assert "233" in data

    # Check Biota (Taxon 1)
    biota = data["1"]
    assert biota["id"] == 1
    assert biota["name"] == "Biota"
    assert biota["aphia_id"] == 1
    assert biota["display_name"] == "Biota"
    assert biota["type"] == "P"
    assert biota["status"] == "A"
    assert biota["rank"] == "Superdomain"
    assert biota["lineage"] == ["Biota"]
    assert biota["id_lineage"] == [1]

    # Check Cyanobacteria (Taxon 233)
    cyano = data["233"]
    assert cyano["id"] == 233
    assert cyano["name"] == "Cyanobacteria"
    assert cyano["aphia_id"] == 146537
    assert cyano["display_name"] == "Cyanobacteria<Negibacteria"
    assert cyano["type"] == "P"
    assert cyano["status"] == "A"
    assert cyano["lineage"] == ["Cyanobacteria", "Negibacteria", "Bacteria", "Biota"]
    assert cyano["id_lineage"] == [233, 100089, 3, 1]

    # 2. Taxon 849 is a renamed phylo taxon (renm_id=233)
    url = WORMSIFICATION_TAXA_SET_URL.format(taxa_ids="849")
    rsp = fastapi.get(url)
    assert rsp.status_code == status.HTTP_200_OK
    data = rsp.json()
    assert "233" in data
    assert data["233"]["aphia_id"] == 146537

    # 3. Test various delimiters (comma, pipe)
    url_comma = WORMSIFICATION_TAXA_SET_URL.format(taxa_ids="1,233")
    rsp_comma = fastapi.get(url_comma)
    assert rsp_comma.status_code == status.HTTP_200_OK
    assert set(rsp_comma.json().keys()) == {"1", "233"}

    url_pipe = WORMSIFICATION_TAXA_SET_URL.format(taxa_ids="1|233")
    rsp_pipe = fastapi.get(url_pipe)
    assert rsp_pipe.status_code == status.HTTP_200_OK
    assert set(rsp_pipe.json().keys()) == {"1", "233"}

    # 4. Non-existent taxon ID
    url_nonexistent = WORMSIFICATION_TAXA_SET_URL.format(taxa_ids="99999999")
    rsp_nonexistent = fastapi.get(url_nonexistent)
    assert rsp_nonexistent.status_code == status.HTTP_200_OK
    assert rsp_nonexistent.json() == {}

    # 5. Authenticated call
    rsp_auth = fastapi.get(url, headers=USER_AUTH)
    assert rsp_auth.status_code == status.HTTP_200_OK
    assert rsp_auth.json() == data
