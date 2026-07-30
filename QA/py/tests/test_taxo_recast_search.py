# noinspection PyPackageRequirements
from starlette import status

from BO.DataLicense import AccessLevelEnum
from DB.TaxoRecast import RecastOperation
from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID, CREATOR_AUTH, CREATOR_USER_ID
from tests.test_import import create_project

TAXORECAST_URL = "/taxo_recast"
TAXORECAST_SEARCH_URL = "/taxo_recast/search"


def add_project_recast(fastapi, prj_id, operation, who=ADMIN_AUTH):
    recast = {
        "from_to": {"12345": 0},
        "doc": {},
    }
    recastreq = {
        "target_id": prj_id,
        "operation": operation.value,
        "recast": recast,
        "is_collection": False,
    }
    rsp = fastapi.put(TAXORECAST_URL, json=recastreq, headers=who)
    assert rsp.status_code == status.HTTP_200_OK


def test_taxo_recast_search_explicit_ids(fastapi):
    """Existing behaviour: among the given project_ids, only the ones with
    a recast for the operation are returned, with their project title."""
    prj_with_recast = create_project(ADMIN_USER_ID, "taxo_recast_search_with")
    prj_without_recast = create_project(ADMIN_USER_ID, "taxo_recast_search_without")
    add_project_recast(fastapi, prj_with_recast, RecastOperation.project_import)

    params = {
        "project_ids": "%d,%d" % (prj_with_recast, prj_without_recast),
        "operation": RecastOperation.project_import.value,
    }
    rsp = fastapi.get(TAXORECAST_SEARCH_URL, headers=ADMIN_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    ret = rsp.json()
    assert [rec["project_id"] for rec in ret] == [prj_with_recast]
    assert ret[0]["project_title"] == "taxo_recast_search_with"
    assert ret[0]["operation"] == RecastOperation.project_import.value
    assert ret[0]["transforms"] == {"12345": 0}


def test_taxo_recast_search_no_ids(fastapi):
    """New behaviour: when project_ids is omitted, only the projects
    readable/administered by the current user are considered."""
    # A project owned (thus administered) by the creator, with a recast
    creator_prj = create_project(
        CREATOR_USER_ID,
        "taxo_recast_search_creator_owned",
        access=AccessLevelEnum.PRIVATE.value,
    )
    add_project_recast(
        fastapi, creator_prj, RecastOperation.project_import, who=CREATOR_AUTH
    )

    # An unrelated, private, admin-owned project, also with a recast
    admin_prj = create_project(
        ADMIN_USER_ID,
        "taxo_recast_search_admin_owned",
        access=AccessLevelEnum.PRIVATE.value,
    )
    add_project_recast(fastapi, admin_prj, RecastOperation.project_import)

    params = {"operation": RecastOperation.project_import.value}

    # The creator only sees its own project
    rsp = fastapi.get(TAXORECAST_SEARCH_URL, headers=CREATOR_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    prj_ids = [rec["project_id"] for rec in rsp.json()]
    assert creator_prj in prj_ids
    assert admin_prj not in prj_ids

    # The admin, being APP_ADMINISTRATOR, sees every project with a recast
    rsp = fastapi.get(TAXORECAST_SEARCH_URL, headers=ADMIN_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    prj_ids = [rec["project_id"] for rec in rsp.json()]
    assert creator_prj in prj_ids
    assert admin_prj in prj_ids


def test_taxo_recast_search_no_ids_no_access(fastapi):
    """A user with no project at all gets an empty list, not an error,
    when project_ids is omitted."""
    admin_prj = create_project(
        ADMIN_USER_ID,
        "taxo_recast_search_no_access",
        access=AccessLevelEnum.PRIVATE.value,
    )
    add_project_recast(fastapi, admin_prj, RecastOperation.project_import)

    params = {"operation": RecastOperation.project_import.value}
    rsp = fastapi.get(TAXORECAST_SEARCH_URL, headers=CREATOR_AUTH, params=params)
    assert rsp.status_code == status.HTTP_200_OK
    prj_ids = [rec["project_id"] for rec in rsp.json()]
    assert admin_prj not in prj_ids
