import compression.zstd as zstd
import shutil
import tarfile
from io import BytesIO
from pathlib import Path

from starlette import status

from FS.UserFilesDir import UserFilesDirectory
from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID, USER_AUTH
from tests.test_import import do_test_import


def _verify_project_restored(fastapi, prj_id: int, expected_obj_count: int) -> None:
    prj_rsp = fastapi.get(f"/projects/{prj_id}", headers=ADMIN_AUTH)
    assert prj_rsp.status_code == status.HTTP_200_OK
    assert prj_rsp.json()["title"] == "Technical import project"

    objs_rsp = fastapi.post(
        f"/object_set/{prj_id}/query",
        headers=ADMIN_AUTH,
        json={},
    )
    assert objs_rsp.status_code == status.HTTP_200_OK
    assert objs_rsp.json()["total_ids"] == expected_obj_count


def test_technical_import(fastapi):
    prj_id = do_test_import(fastapi, "Technical import project")

    objs_rsp = fastapi.post(
        f"/object_set/{prj_id}/query",
        headers=ADMIN_AUTH,
        json={},
    )
    assert objs_rsp.status_code == status.HTTP_200_OK
    expected_obj_count = objs_rsp.json()["total_ids"]
    assert expected_obj_count > 0

    # Export technical archive
    exp_rsp = fastapi.get(
        f"/admin/technical_export?project_id={prj_id}", headers=ADMIN_AUTH
    )
    assert exp_rsp.status_code == status.HTTP_200_OK
    zst_bytes = exp_rsp.content

    # Non-admin cannot call technical_import
    unauth_rsp = fastapi.post(
        "/admin/technical_import?archive_name=anything.tar.zst", headers=USER_AUTH
    )
    assert unauth_rsp.status_code == status.HTTP_403_FORBIDDEN

    # Missing archive -> 404
    missing_rsp = fastapi.post(
        "/admin/technical_import?archive_name=does_not_exist.tar.zst",
        headers=ADMIN_AUTH,
    )
    assert missing_rsp.status_code == status.HTTP_404_NOT_FOUND

    # Path traversal -> 422
    trav_rsp = fastapi.post(
        "/admin/technical_import?archive_name=../escape.tar.zst",
        headers=ADMIN_AUTH,
    )
    assert trav_rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)

    # 1. Restore from .tar.zst
    zst_name = f"test_tek_{prj_id}.tar.zst"
    zst_path = user_root / zst_name
    zst_path.write_bytes(zst_bytes)
    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK
        assert (
            fastapi.get(f"/projects/{prj_id}", headers=ADMIN_AUTH).status_code
            == status.HTTP_404_NOT_FOUND
        )

        imp_rsp = fastapi.post(
            f"/admin/technical_import?archive_name={zst_name}",
            headers=ADMIN_AUTH,
        )
        assert imp_rsp.status_code == status.HTTP_200_OK, imp_rsp.text
        body = imp_rsp.json()
        assert body["project_id"] == prj_id
        assert body["tables"]["projects"] == 1
        assert body["tables"]["obj_head"] == expected_obj_count
        assert body["vault_files"] > 0
        _verify_project_restored(fastapi, prj_id, expected_obj_count)
    finally:
        zst_path.unlink(missing_ok=True)

    # 2. Restore from plain .tar
    tar_name = f"test_tek_{prj_id}.tar"
    tar_path = user_root / tar_name
    tar_bytes = zstd.decompress(zst_bytes)
    tar_path.write_bytes(tar_bytes)
    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        imp_rsp = fastapi.post(
            f"/admin/technical_import?archive_name={tar_name}",
            headers=ADMIN_AUTH,
        )
        assert imp_rsp.status_code == status.HTTP_200_OK, imp_rsp.text
        body = imp_rsp.json()
        assert body["project_id"] == prj_id
        assert body["tables"]["obj_head"] == expected_obj_count
        assert body["vault_files"] > 0
        _verify_project_restored(fastapi, prj_id, expected_obj_count)
    finally:
        tar_path.unlink(missing_ok=True)

    # 3. Restore from extracted .tar directory (directory named *.tar)
    dir_name = f"test_tek_{prj_id}_dir.tar"
    dir_path = user_root / dir_name
    dir_path.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as tf:
        tf.extractall(path=dir_path, filter="data")
    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        imp_rsp = fastapi.post(
            f"/admin/technical_import?archive_name={dir_name}",
            headers=ADMIN_AUTH,
        )
        assert imp_rsp.status_code == status.HTTP_200_OK, imp_rsp.text
        body = imp_rsp.json()
        assert body["project_id"] == prj_id
        assert body["tables"]["obj_head"] == expected_obj_count
        assert body["vault_files"] > 0
        _verify_project_restored(fastapi, prj_id, expected_obj_count)
    finally:
        shutil.rmtree(dir_path, ignore_errors=True)
