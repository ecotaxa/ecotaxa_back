from fastapi import status
import pandas as pd

from API_operations.CRUD.ObjectParents import SamplesService
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import create_project, do_import_uvp6
from tests.test_objectset_query import _prj_query
from tests.test_similarity_search import save_features

PATCH_URL = "/projects/{project_id}"


def _admin_min_user(fastapi, prj_id):
    # The project already has the admin as contact/manager from creation,
    # so its embedded MinUserModel representation can be reused as-is.
    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    prj_json = fastapi.get(get_url, headers=ADMIN_AUTH).json()
    return prj_json["contact"]


def test_patch_project_empty_body(fastapi):
    # No field is required: an empty patch is a valid no-op.
    # A bare project (no import) is enough, no need for actual data.
    prj_id = create_project(ADMIN_USER_ID, "Patch Test Project Empty")
    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    before = fastapi.get(get_url, headers=ADMIN_AUTH).json()
    url = PATCH_URL.format(project_id=prj_id)
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    after = fastapi.get(get_url, headers=ADMIN_AUTH).json()
    assert before == after


def test_patch_project_title_only(fastapi):
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test Project")
    url = PATCH_URL.format(project_id=prj_id)
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"title": "Patched Title"})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text

    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(get_url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    assert prj_json["title"] == "Patched Title"
    # Untouched fields must be unaffected
    assert prj_json["status"] == "Annotate"


def test_patch_project_managers_without_contact(fastapi):
    # Reproduces the former NameError: patching managers/annotators/viewers
    # without also patching 'contact' in the same request.
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test Project Managers")
    url = PATCH_URL.format(project_id=prj_id)
    body = {"managers": [_admin_min_user(fastapi, prj_id)]}
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json=body)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text

    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(get_url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    assert len(prj_json["managers"]) == 1
    assert prj_json["managers"][0]["id"] == ADMIN_USER_ID


def test_patch_project_contact_and_managers(fastapi):
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test Project Contact")
    url = PATCH_URL.format(project_id=prj_id)
    admin_user = _admin_min_user(fastapi, prj_id)
    body = {"managers": [admin_user], "contact": admin_user}
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json=body)
    assert rsp.status_code == status.HTTP_200_OK, rsp.text

    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(get_url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    assert prj_json["contact"]["id"] == ADMIN_USER_ID
    assert prj_json["managers"][0]["id"] == ADMIN_USER_ID


def test_patch_project_cnn_image_position(fastapi):
    prj_id = create_project(ADMIN_USER_ID, "Patch Test Project CNN Image Pos")
    url = PATCH_URL.format(project_id=prj_id)
    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)

    # Set valid cnn_image_position >= 1
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": 3})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    assert fastapi.get(get_url, headers=ADMIN_AUTH).json()["cnn_image_position"] == 3

    # Reject invalid cnn_image_position < 1
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": 0})
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, rsp.text

    # Reset to None
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": None})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    assert fastapi.get(get_url, headers=ADMIN_AUTH).json()["cnn_image_position"] is None


def _count_features(obj_ids):
    with SamplesService() as sce:
        return (
            sce.session.query(ObjectCNNFeatureVector)
            .filter(ObjectCNNFeatureVector.objcnnid.in_(obj_ids))
            .count()
        )


def _insert_features(obj_ids):
    features_df = pd.DataFrame(
        [[(i + 1) * 0.1] * 50 for i in range(len(obj_ids))], index=obj_ids
    )
    with SamplesService() as sce:
        n_inserts = save_features(sce.session, features_df)
        assert n_inserts == len(obj_ids)
        sce.session.commit()


def test_patch_project_cnn_image_position_clears_features(fastapi):
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test CNN Image Pos Features")
    obj_ids = _prj_query(fastapi, ADMIN_AUTH, prj_id)
    assert len(obj_ids) > 0
    url = PATCH_URL.format(project_id=prj_id)

    _insert_features(obj_ids)
    assert _count_features(obj_ids) == len(obj_ids)

    # None -> 1 is not a real change: features must remain
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": 1})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    assert _count_features(obj_ids) == len(obj_ids)

    # 1 -> None is not a real change: features must remain
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": None})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    assert _count_features(obj_ids) == len(obj_ids)

    # None -> 2 is a real change: features must be erased
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": 2})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    assert _count_features(obj_ids) == 0

    # Re-insert and patch 2 -> 2 (no change): features must remain
    _insert_features(obj_ids)
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": 2})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    assert _count_features(obj_ids) == len(obj_ids)

    # 2 -> None (real change back to default 1): features must be erased
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": None})
    assert rsp.status_code == status.HTTP_200_OK, rsp.text
    assert _count_features(obj_ids) == 0


def test_patch_project_cnn_image_position_validation(fastapi):
    prj_id, _ = do_import_uvp6(fastapi, "Patch Test CNN Image Pos Validation")
    obj_ids = _prj_query(fastapi, ADMIN_AUTH, prj_id)
    assert len(obj_ids) == 15
    url = PATCH_URL.format(project_id=prj_id)
    get_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)

    _insert_features(obj_ids)
    assert _count_features(obj_ids) == len(obj_ids)

    # All 15 objects in UVP6_example have 2 images, so position 3 must fail
    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": 3})
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, rsp.text
    assert "15" in rsp.json()["detail"]
    # Neither project field nor existing features should be modified on failure
    assert fastapi.get(get_url, headers=ADMIN_AUTH).json()["cnn_image_position"] is None
    assert _count_features(obj_ids) == len(obj_ids)

    # Delete one image from one object so it only has 1 image; now position 2 must fail for 1 object
    from DB.Image import Image

    with SamplesService() as sce:
        img_to_del = (
            sce.session.query(Image)
            .filter(Image.objid == obj_ids[0])
            .order_by(Image.imgrank.desc())
            .first()
        )
        assert img_to_del is not None
        sce.session.delete(img_to_del)
        sce.session.commit()

    rsp = fastapi.patch(url, headers=ADMIN_AUTH, json={"cnn_image_position": 2})
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, rsp.text
    assert "1 object(s)" in rsp.json()["detail"]
    assert fastapi.get(get_url, headers=ADMIN_AUTH).json()["cnn_image_position"] is None
    assert _count_features(obj_ids) == len(obj_ids)
