import json

# noinspection PyPackageRequirements
from starlette import status

from tests.credentials import ADMIN_AUTH
from tests.test_export_emodnet import create_test_collection
from API_models.taxonomy import TaxoRecastRsp, TaxonomyRecastReq
from DB.TaxoRecast import RecastOperation

PROJECT_EXPORT_EMODNET_URL = "/export/darwin_core?dry_run=False"

COLLECTION_CREATE_URL = "/collections/create"
COLLECTION_TAXO_RECAST_URL = "/taxo_recast"


def test_collection_taxo_recast(fastapi):
    coll_id, coll_title, prj_id = create_test_collection(fastapi, "api_ok")
    url = COLLECTION_TAXO_RECAST_URL
    # Example write
    taxo_recast = TaxoRecastRsp(
        from_to={12345: None, 6789: 123}, doc={6789: "Bump up one level"}
    )
    recast = TaxonomyRecastReq(
        target_id=coll_id,
        operation=RecastOperation.settings,
        recast=taxo_recast,
        is_collection=True,
    )
    rsp = fastapi.put(url, headers=ADMIN_AUTH, data=recast)
    assert rsp.status_code == status.HTTP_200_OK
    # Re-read
    rsp2 = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp2.status_code == status.HTTP_200_OK
    assert rsp2.json() == json.loads(json.dumps(recast))


def test_collection_taxo_recast_endpoint(fastapi):
    coll_id, coll_title, prj_id = create_test_collection(fastapi, "api_ko")
    url = COLLECTION_TAXO_RECAST_URL
    # Example wrong write
    recast = {
        "from_to": {12345: None, 6789: 123, "a:": 12.3},
        "doc": {6789: "Bump up one level"},
    }
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    recast = {
        "from_cto": {12345: None, 6789: 123, "12": 127},
        "doc": {6789: "Bump up one level"},
    }
    rsp2 = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    recast = {
        "from_to": {12345: None, 6789: 123, "12": 127},
        "no_doc": {6789: "Bump up one level"},
    }
    rsp2 = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
