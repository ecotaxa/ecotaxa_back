import compression.zstd as zstd
import json
import shutil
import tarfile
from io import BytesIO

from starlette import status

from FS.UserFilesDir import UserFilesDirectory
from tests.api_wrappers import api_get_log_file, api_wait_for_stable_job
from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID, USER_AUTH
from tests.export_shared import JOB_DOWNLOAD_URL
from tests.test_import import do_test_import


def _export_technical_archive(fastapi, prj_id: int) -> bytes:
    exp_rsp = fastapi.post(
        f"/admin/technical_export?project_id={prj_id}", headers=ADMIN_AUTH
    )
    assert exp_rsp.status_code == status.HTTP_200_OK
    job_id = exp_rsp.json()
    job = api_wait_for_stable_job(fastapi, job_id)
    assert job.state == "F", job
    dl_rsp = fastapi.get(JOB_DOWNLOAD_URL.format(job_id=job_id), headers=ADMIN_AUTH)
    assert dl_rsp.status_code == status.HTTP_200_OK
    return dl_rsp.content


def _run_technical_import(fastapi, archive_name: str):
    imp_rsp = fastapi.post(
        f"/admin/technical_import?archive_name={archive_name}",
        headers=ADMIN_AUTH,
    )
    assert imp_rsp.status_code == status.HTTP_200_OK, imp_rsp.text
    job_id = imp_rsp.json()
    assert isinstance(job_id, int)
    return api_wait_for_stable_job(fastapi, job_id)


def _assert_import_failed(fastapi, job, expected_substring: str) -> None:
    assert job.state == "E", job
    assert job.progress_msg == "1 error(s) during run", job
    assert len(job.errors) == 1, job.errors
    assert expected_substring in job.errors[0], job.errors
    log_lines = api_get_log_file(fastapi, job.id)
    assert any(
        "ERROR" in line and "Technical import failed:" in line and expected_substring in line
        for line in log_lines
    ), log_lines


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
    zst_bytes = _export_technical_archive(fastapi, prj_id)

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

        job = _run_technical_import(fastapi, zst_name)
        assert job.state == "F", job
        assert job.progress_pct == 100
        assert job.progress_msg == "Done"
        body = job.result
        assert body is not None
        assert body["project_id"] == prj_id
        assert body["tables"]["projects"] == 1
        assert body["tables"]["obj_head"] == expected_obj_count
        assert body["vault_files"] > 0
        _verify_project_restored(fastapi, prj_id, expected_obj_count)
    finally:
        zst_path.unlink(missing_ok=True)

    # 2. Uncompressed .tar and extracted directory are rejected -> job Error
    tar_name = f"test_tek_{prj_id}.tar"
    tar_path = user_root / tar_name
    tar_bytes = zstd.decompress(zst_bytes)
    tar_path.write_bytes(tar_bytes)
    dir_name = f"test_tek_{prj_id}_dir"
    dir_path = user_root / dir_name
    dir_path.mkdir(parents=True, exist_ok=True)
    try:
        for bad_name in (tar_name, dir_name):
            bad_job = _run_technical_import(fastapi, bad_name)
            _assert_import_failed(fastapi, bad_job, "Unsupported archive format")
    finally:
        tar_path.unlink(missing_ok=True)
        shutil.rmtree(dir_path, ignore_errors=True)

    # 3. Restore from .tar.zst with reordered columns
    reordered_tar_name = f"test_tek_{prj_id}_reordered.tar.zst"
    reordered_tar_path = user_root / reordered_tar_name
    tables_to_reverse = {"03_users.copy": "users", "06_projects.copy": "projects"}
    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as src_tf:
        members_data = []
        meta_bytes = b""
        for member in src_tf:
            if not member.isfile():
                continue
            f = src_tf.extractfile(member)
            assert f is not None
            data = f.read()
            if member.name == "0_metadata.json":
                meta_bytes = data
            else:
                members_data.append((member.name, data))

    meta_obj = json.loads(meta_bytes.decode("utf-8"))
    for tbl_meta in meta_obj["tables"]:
        if tbl_meta["name"] in tables_to_reverse.values():
            tbl_meta["columns"] = list(reversed(tbl_meta["columns"]))

    with tarfile.open(name=reordered_tar_path, mode="w:zst") as dst_tf:
        new_meta_bytes = json.dumps(meta_obj).encode("utf-8")
        ti_meta = tarfile.TarInfo(name="0_metadata.json")
        ti_meta.size = len(new_meta_bytes)
        dst_tf.addfile(ti_meta, BytesIO(new_meta_bytes))
        for name, data in members_data:
            if name in tables_to_reverse:
                lines = data.decode("utf-8").splitlines()
                reversed_lines = [
                    "\t".join(reversed(line.split("\t"))) for line in lines if line
                ]
                data = ("\n".join(reversed_lines) + "\n").encode("utf-8") if reversed_lines else b""
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            dst_tf.addfile(ti, BytesIO(data))

    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        job = _run_technical_import(fastapi, reordered_tar_name)
        assert job.state == "F", job
        body = job.result
        assert body is not None
        assert body["project_id"] == prj_id
        assert body["tables"]["projects"] == 1
        assert body["tables"]["obj_head"] == expected_obj_count
        assert body["vault_files"] > 0
        _verify_project_restored(fastapi, prj_id, expected_obj_count)
    finally:
        reordered_tar_path.unlink(missing_ok=True)


def test_technical_import_resets_identity_and_serial_sequences(fastapi):
    from datetime import datetime
    from API_operations.helpers.Service import Service
    from DB.TaxoRecast import RecastOperation, TaxoRecast
    from DB.Training import Training

    prj_id = do_test_import(fastapi, "Seq reset project")

    tar_bytes = zstd.decompress(_export_technical_archive(fastapi, prj_id))

    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)
    seq_tar_name = f"test_tek_{prj_id}_seq.tar.zst"
    seq_tar_path = user_root / seq_tar_name

    recast_id_val = 500
    training_id_val = 500

    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as src_tf:
        with tarfile.open(name=seq_tar_path, mode="w:zst") as dst_tf:
            for member in src_tf:
                if not member.isfile():
                    continue
                f = src_tf.extractfile(member)
                assert f is not None
                data = f.read()
                if member.name.endswith("_taxo_recast.copy"):
                    data = (
                        f"{recast_id_val}\t\\N\t{prj_id}\t"
                        f"{RecastOperation.project_export.value}\t{{}}\t{{}}\n"
                    ).encode("utf-8")
                elif member.name.endswith("_training.copy"):
                    data = (
                        f"{training_id_val}\t{prj_id}\t{ADMIN_USER_ID}\t"
                        f"2026-01-01 00:00:00\t2026-01-01 00:01:00\ttest_path\n"
                    ).encode("utf-8")
                ti = tarfile.TarInfo(name=member.name)
                ti.size = len(data)
                dst_tf.addfile(ti, BytesIO(data))

    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        job = _run_technical_import(fastapi, seq_tar_name)
        assert job.state == "F", job
        body = job.result
        assert body is not None
        assert body["tables"]["taxo_recast"] == 1
        assert body["tables"]["training"] == 1

        with Service() as sce:
            new_recast = TaxoRecast(
                project_id=prj_id,
                operation=RecastOperation.project_export.value,
                transforms={},
                documentation={},
            )
            new_training = Training(
                projid=prj_id,
                training_author=ADMIN_USER_ID,
                training_start=datetime(2026, 1, 2, 0, 0, 0),
                training_end=datetime(2026, 1, 2, 0, 1, 0),
                training_path="test_path_2",
            )
            sce.session.add(new_recast)
            sce.session.add(new_training)
            sce.session.flush()
            assert new_recast.recast_id > recast_id_val
            assert new_training.training_id > training_id_val
            sce.session.rollback()
    finally:
        seq_tar_path.unlink(missing_ok=True)


def test_technical_import_requires_table_in_metadata(fastapi):
    prj_id = do_test_import(fastapi, "Missing metadata project")

    tar_bytes = zstd.decompress(_export_technical_archive(fastapi, prj_id))

    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)

    # 1. Archive without 0_metadata.json -> 422
    no_meta_tar_name = f"test_tek_{prj_id}_no_meta.tar.zst"
    no_meta_tar_path = user_root / no_meta_tar_name
    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as src_tf:
        with tarfile.open(name=no_meta_tar_path, mode="w:zst") as dst_tf:
            for member in src_tf:
                if not member.isfile() or member.name == "0_metadata.json":
                    continue
                f = src_tf.extractfile(member)
                assert f is not None
                data = f.read()
                ti = tarfile.TarInfo(name=member.name)
                ti.size = len(data)
                dst_tf.addfile(ti, BytesIO(data))

    # 2. Archive where 'projects' is omitted from 0_metadata.json -> 422
    missing_tbl_tar_name = f"test_tek_{prj_id}_missing_tbl.tar.zst"
    missing_tbl_tar_path = user_root / missing_tbl_tar_name
    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as src_tf:
        with tarfile.open(name=missing_tbl_tar_path, mode="w:zst") as dst_tf:
            for member in src_tf:
                if not member.isfile():
                    continue
                f = src_tf.extractfile(member)
                assert f is not None
                data = f.read()
                if member.name == "0_metadata.json":
                    meta_obj = json.loads(data.decode("utf-8"))
                    meta_obj["tables"] = [
                        t for t in meta_obj["tables"] if t["name"] != "projects"
                    ]
                    data = json.dumps(meta_obj).encode("utf-8")
                ti = tarfile.TarInfo(name=member.name)
                ti.size = len(data)
                dst_tf.addfile(ti, BytesIO(data))

    try:
        for name, expected in (
            (no_meta_tar_name, "before 0_metadata.json"),
            (missing_tbl_tar_name, "Missing metadata columns for table 'projects'"),
        ):
            job = _run_technical_import(fastapi, name)
            _assert_import_failed(fastapi, job, expected)
    finally:
        no_meta_tar_path.unlink(missing_ok=True)
        missing_tbl_tar_path.unlink(missing_ok=True)


def test_technical_import_rejects_unexpected_or_out_of_order_tables(fastapi):
    prj_id = do_test_import(fastapi, "Unexpected table order project")

    tar_bytes = zstd.decompress(_export_technical_archive(fastapi, prj_id))

    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)

    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as src_tf:
        members = []
        for member in src_tf:
            if not member.isfile():
                continue
            f = src_tf.extractfile(member)
            assert f is not None
            members.append((member.name, f.read()))

    # 1. .copy file before 0_metadata.json -> 422
    before_meta_name = f"test_tek_{prj_id}_before_meta.tar.zst"
    before_meta_path = user_root / before_meta_name
    with tarfile.open(name=before_meta_path, mode="w:zst") as dst_tf:
        for name, data in reversed(members):
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            dst_tf.addfile(ti, BytesIO(data))

    # 2. Unknown .copy file -> 422
    unknown_tbl_name = f"test_tek_{prj_id}_unknown_tbl.tar.zst"
    unknown_tbl_path = user_root / unknown_tbl_name
    with tarfile.open(name=unknown_tbl_path, mode="w:zst") as dst_tf:
        for name, data in members:
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            dst_tf.addfile(ti, BytesIO(data))
            if name == "0_metadata.json":
                bogus = b"1\tfoo\n"
                ti_bogus = tarfile.TarInfo(name="99_unknown_table.copy")
                ti_bogus.size = len(bogus)
                dst_tf.addfile(ti_bogus, BytesIO(bogus))

    # 3. Out-of-order .copy file (03_users.copy after 06_projects.copy) -> 422
    out_of_order_name = f"test_tek_{prj_id}_out_of_order.tar.zst"
    out_of_order_path = user_root / out_of_order_name
    swapped = list(members)
    idx_users = next(i for i, (n, _) in enumerate(swapped) if n == "03_users.copy")
    idx_projects = next(i for i, (n, _) in enumerate(swapped) if n == "06_projects.copy")
    swapped[idx_users], swapped[idx_projects] = swapped[idx_projects], swapped[idx_users]
    with tarfile.open(name=out_of_order_path, mode="w:zst") as dst_tf:
        for name, data in swapped:
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            dst_tf.addfile(ti, BytesIO(data))

    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        for name, expected in (
            (before_meta_name, "before 0_metadata.json"),
            (unknown_tbl_name, "Unexpected table file '99_unknown_table.copy'"),
            (out_of_order_name, "Unexpected out-of-order table 'taxonomy'"),
        ):
            job = _run_technical_import(fastapi, name)
            _assert_import_failed(fastapi, job, expected)
    finally:
        before_meta_path.unlink(missing_ok=True)
        unknown_tbl_path.unlink(missing_ok=True)
        out_of_order_path.unlink(missing_ok=True)
