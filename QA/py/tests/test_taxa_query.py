import logging

from starlette import status

TAXA_QUERY_URL = "/taxa/search?query={query}&project_id={project_id}"


def test_taxotree_query(config, database, fastapi, caplog):
    """ This depends on the DB which has a subset of the production one """
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import
    prj_id = test_import(config, database, caplog, "Test taxo query")

    url = TAXA_QUERY_URL.format(project_id=prj_id, query="")
    # Unauthenticaed call
    rsp = fastapi.get(url, json={})
    # Security barrier
    assert rsp.status_code == status.HTTP_200_OK
