import logging
from urllib.parse import quote_plus

from starlette import status

TAXA_SEARCH_URL = "/taxon_set/search?query={query}&project_id={project_id}"
TAXA_QUERY_URL = "/taxon/{taxon_id}"
TAXA_SET_QUERY_URL = "/taxon_set/query?ids={taxa_ids}"
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
    assert rsp.json() == [{'id': 233, 'pr': 0, 'renm_id': None, 'text': 'Cyanobacteria<Bacteria'},
                          {'id': 849, 'pr': 0, 'renm_id': None, 'text': 'Cyanobacteria<Proteobacteria'},
                          {'id': 2396, 'pr': 0, 'renm_id': None, 'text': 'Cyanophora'},
                          {'id': 1680, 'pr': 0, 'renm_id': None, 'text': 'Cyanophyceae'},
                          {'id': 2395, 'pr': 0, 'renm_id': None, 'text': 'Cyanoptyche'}]


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
    assert rsp.json() == {'children': [5141],
                          'display_name': 'Cyanobacteria<Proteobacteria',
                          'id': 849,
                          'lineage': ['Cyanobacteria', 'Proteobacteria', 'Bacteria', 'living'],
                          'id_lineage': [849, 96, 3, 1],
                          'name': 'Cyanobacteria',
                          'nb_children_objects': 0,
                          'nb_objects': 0,
                          'renm_id': None,
                          'type': 'P'}


def test_worms_query(config, database, fastapi, caplog):
    url = WORMS_TAXA_QUERY_URL.format(aphia_id=128586)
    # Unauthenticated call
    rsp = fastapi.get(url)
    assert rsp.json() == {'children': [],
                          'display_name': 'Oncaeidae',
                          'id': 128586,
                          'lineage': ['Oncaeidae',
                                      'Ergasilida',
                                      'Cyclopoida',
                                      'Podoplea',
                                      'Neocopepoda',
                                      'Copepoda',
                                      'Hexanauplia',
                                      'Multicrustacea',
                                      'Crustacea',
                                      'Arthropoda',
                                      'Animalia',
                                      'Biota'],
                          'id_lineage': [128586,
                                         1381349,
                                         1101,
                                         155879,
                                         155876,
                                         1080,
                                         889925,
                                         845959,
                                         1066,
                                         1065,
                                         2,
                                         1],
                          'name': 'Oncaeidae',
                          'nb_children_objects': 0,
                          'nb_objects': 0,
                          'renm_id': None,
                          'type': 'P'}
