import json

# noinspection PyPackageRequirements
from starlette import status

from tests.credentials import (
    ADMIN_AUTH,
    CREATOR_AUTH,
    ORDINARY_USER_USER_ID,
    ORDINARY_USER2_USER_ID,
    USER2_AUTH,
    USER_AUTH,
)
from tests.test_import import do_test_import
from tests.test_export_emodnet import create_test_collection
from DB.TaxoRecast import RecastOperation

PROJECT_EXPORT_EMODNET_URL = "/export/darwin_core?dry_run=False"

COLLECTION_CREATE_URL = "/collections/create"
TAXORECAST_URL = "/taxo_recast"


def test_collection_taxo_recast(fastapi):
    coll_id, coll_title, prj_id = create_test_collection(fastapi, "api_ok")
    url = TAXORECAST_URL
    taxo_recast = {
        "from_to": {
            "12345": 0,
            "6789": 25828,
        },
        "doc": {"6789": "Bump up one level"},
    }
    recast = {
        "target_id": int(coll_id),
        "operation": RecastOperation.dwca_export_occurrence.value,
        "recast": taxo_recast,
        "is_collection": True,
    }
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp.status_code == status.HTTP_200_OK
    # Example write
    taxo_recast = {
        "from_to": {
            "12345": 0,
            "6789": 25828,
        },
        "doc": {"6789": "Bump up one level"},
    }
    recast = {
        "target_id": int(coll_id),
        "operation": RecastOperation.dwca_export_emof.value,
        "recast": taxo_recast,
        "is_collection": True,
    }
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp.status_code == status.HTTP_200_OK
    # Re-read
    payload = {
        "target_id": int(coll_id),
        "operation": RecastOperation.dwca_export_emof.value,
        "is_collection": True,
    }
    rsp2 = fastapi.get(url, headers=ADMIN_AUTH, params=payload)
    assert rsp2.status_code == status.HTTP_200_OK
    assert rsp2.json() == taxo_recast


def test_collection_taxo_recast_endpoint(fastapi):
    coll_id, coll_title, prj_id = create_test_collection(fastapi, "api_ko")
    url = TAXORECAST_URL
    # Example wrong write
    recast = {
        "from_to": {"12345": 0, "6789": 123, "a:": 12.3},
        "doc": {"6789": "Bump up one level"},
    }
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    recast = {
        "from_to": {"12345": 0, "6789": 123, 12: 127},
        "doc": {"6789": "Bump up one level"},
    }
    rsp2 = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    recast = {
        "from_to": {"12345": 0, "6789": 123, "12": 127},
        "no_doc": {"6789": "Bump up one level"},
    }
    rsp2 = fastapi.put(url, headers=ADMIN_AUTH, json=recast)
    assert rsp2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def _add_privilege(prj_id, user_id, privilege):
    from API_operations.CRUD.Projects import ProjectsService
    from DB.ProjectPrivilege import ProjectPrivilege

    with ProjectsService() as sce:
        priv = ProjectPrivilege()
        priv.projid = prj_id
        priv.member = user_id
        priv.privilege = privilege
        sce.session.add(priv)
        sce.session.commit()


def _remove_privilege(prj_id, user_id):
    from API_operations.CRUD.Projects import ProjectsService
    from DB.ProjectPrivilege import ProjectPrivilege

    with ProjectsService() as sce:
        sce.session.query(ProjectPrivilege).filter(
            ProjectPrivilege.projid == prj_id, ProjectPrivilege.member == user_id
        ).delete()
        sce.session.commit()


def test_collection_taxo_recast_members(fastapi):
    # On a collection, the right is checked on each of its projects with the member's
    # privilege there. The ids were passed as rows, so no privilege ever matched.
    # A collection needs samples
    prj_id = do_test_import(fastapi, "Recast members project")
    rsp = fastapi.patch(f"/projects/{prj_id}", headers=ADMIN_AUTH, json={"access": "0"})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    rsp = fastapi.get(f"/projects/{prj_id}", headers=ADMIN_AUTH)
    assert rsp.json()["access"] == "0"
    rsp = fastapi.post(
        COLLECTION_CREATE_URL,
        headers=ADMIN_AUTH,
        json={"title": "Recast members collection", "project_ids": [prj_id]},
    )
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    coll_id = rsp.json()
    _add_privilege(prj_id, ORDINARY_USER_USER_ID, "Manage")
    _add_privilege(prj_id, ORDINARY_USER2_USER_ID, "View")
    # Other tests (e.g. test_guests) expect these users to manage nothing
    try:
        recast = {
            "target_id": coll_id,
            "operation": RecastOperation.collection_export.value,
            "recast": {"from_to": {"6789": 25828}, "doc": {}},
            "is_collection": True,
        }
        read = {
            "target_id": coll_id,
            "operation": RecastOperation.collection_export.value,
            "is_collection": True,
        }
        # Manage on the project: may update, and read
        rsp = fastapi.put(TAXORECAST_URL, headers=USER_AUTH, json=recast)
        assert rsp.status_code == status.HTTP_200_OK
        rsp = fastapi.get(TAXORECAST_URL, headers=USER_AUTH, params=read)
        assert rsp.status_code == status.HTTP_200_OK
        assert rsp.json()["from_to"] == {"6789": 25828}
        # View on the PRIVATE project: may read, not update
        rsp = fastapi.get(TAXORECAST_URL, headers=USER2_AUTH, params=read)
        assert rsp.status_code == status.HTTP_200_OK
        rsp = fastapi.put(TAXORECAST_URL, headers=USER2_AUTH, json=recast)
        assert rsp.status_code == status.HTTP_403_FORBIDDEN
        # Active, but no privilege on the PRIVATE project: may not even read
        rsp = fastapi.get(TAXORECAST_URL, headers=CREATOR_AUTH, params=read)
        assert rsp.status_code == status.HTTP_403_FORBIDDEN
    finally:
        _remove_privilege(prj_id, ORDINARY_USER_USER_ID)
        _remove_privilege(prj_id, ORDINARY_USER2_USER_ID)


def test_patch_project_access(fastapi):
    # PATCH used to answer 200 but ignore "access"
    prj_id = do_test_import(fastapi, "Patch access project")
    for access in ("2", "0"):
        rsp = fastapi.patch(
            f"/projects/{prj_id}", headers=ADMIN_AUTH, json={"access": access}
        )
        assert rsp.status_code == status.HTTP_200_OK, rsp.text
        rsp = fastapi.get(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert rsp.json()["access"] == access
