import logging
from urllib.parse import urlencode, quote_plus

from starlette import status

TAXA_SEARCH_URL = "/taxa/search?query={query}&project_id={project_id}"
TAXA_QUERY_URL = "/taxa/{taxon_id}"
WORMS_TAXA_QUERY_URL = "/worms/{aphia_id}"


def test_taxotree_query(config, database, fastapi, caplog):
    """ This depends on the DB which has a subset of the production one """
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import
    prj_id = test_import(config, database, caplog, "Test taxo search")

    url = TAXA_SEARCH_URL.format(project_id=prj_id, query="")
    # Unauthenticated call
    rsp = fastapi.get(url, json={})
    # Security barrier
    assert rsp.status_code == status.HTTP_200_OK

    url = TAXA_SEARCH_URL.format(project_id=prj_id, query=quote_plus("cyano<living"))
    # Unauthenticated call
    rsp = fastapi.get(url, json={})
    assert rsp.json() == [{'id': 233, 'pr': 0, 'text': 'Cyanobacteria<Bacteria'},
                          {'id': 849, 'pr': 0, 'text': 'Cyanobacteria<Proteobacteria'},
                          {'id': 2396, 'pr': 0, 'text': 'Cyanophora'},
                          {'id': 1680, 'pr': 0, 'text': 'Cyanophyceae'},
                          {'id': 2395, 'pr': 0, 'text': 'Cyanoptyche'}]


def test_taxo_query(config, database, fastapi, caplog):
    """ This depends on the DB which has a subset of the production one """
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import
    prj_id = test_import(config, database, caplog, "Test taxo query")

    url = TAXA_QUERY_URL.format(taxon_id=849)
    # Unauthenticated call
    rsp = fastapi.get(url)
    # Security barrier
    assert rsp.status_code == status.HTTP_200_OK

    url = TAXA_QUERY_URL.format(taxon_id=849)
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.json() == {'display_name': 'Cyanobacteria<Proteobacteria',
                          'id': 849,
                          'lineage': ['Cyanobacteria', 'Proteobacteria', 'Bacteria', 'living']}


def test_worms_query(config, database, fastapi, caplog):
    url = WORMS_TAXA_QUERY_URL.format(aphia_id=128586)
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.json() == {'display_name': 'Oncaeidae', 'id': 128586, 'lineage': []}
