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


def _run_technical_import(
    fastapi, archive_name: str, target_project_id: int | None = None
):
    url = f"/admin/technical_import?archive_name={archive_name}"
    if target_project_id is not None:
        url += f"&target_project_id={target_project_id}"
    imp_rsp = fastapi.post(
        url,
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
            assert new_recast.recast_id > 0
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

    # 3. Archive where 'project_id' is omitted from 0_metadata.json -> failure
    missing_prj_tar_name = f"test_tek_{prj_id}_missing_prj.tar.zst"
    missing_prj_tar_path = user_root / missing_prj_tar_name
    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as src_tf:
        with tarfile.open(name=missing_prj_tar_path, mode="w:zst") as dst_tf:
            for member in src_tf:
                if not member.isfile():
                    continue
                f = src_tf.extractfile(member)
                assert f is not None
                data = f.read()
                if member.name == "0_metadata.json":
                    meta_obj = json.loads(data.decode("utf-8"))
                    meta_obj.pop("project_id", None)
                    data = json.dumps(meta_obj).encode("utf-8")
                ti = tarfile.TarInfo(name=member.name)
                ti.size = len(data)
                dst_tf.addfile(ti, BytesIO(data))

    try:
        for name, expected in (
            (no_meta_tar_name, "before 0_metadata.json"),
            (missing_tbl_tar_name, "Missing metadata columns for table 'projects'"),
            (missing_prj_tar_name, "Missing project_id in 0_metadata.json"),
        ):
            job = _run_technical_import(fastapi, name)
            _assert_import_failed(fastapi, job, expected)
    finally:
        no_meta_tar_path.unlink(missing_ok=True)
        missing_tbl_tar_path.unlink(missing_ok=True)
        missing_prj_tar_path.unlink(missing_ok=True)


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


def test_technical_import_to_target_project(fastapi):
    from DB.Acquisition import ACQ_PRJ_OFFSET
    from DB.Object import OBJ_PRJ_OFFSET
    from DB.Sample import SAM_PRJ_OFFSET

    prj_id = do_test_import(fastapi, "Technical move project")

    objs_rsp = fastapi.post(
        f"/object_set/{prj_id}/query",
        headers=ADMIN_AUTH,
        json={},
    )
    assert objs_rsp.status_code == status.HTTP_200_OK
    expected_obj_count = objs_rsp.json()["total_ids"]
    assert expected_obj_count > 0

    zst_bytes = _export_technical_archive(fastapi, prj_id)
    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)
    zst_name = f"test_tek_move_{prj_id}.tar.zst"
    zst_path = user_root / zst_name
    zst_path.write_bytes(zst_bytes)

    new_prj_id = prj_id + 100
    try:
        # Invalid target_project_id -> 422
        bad_rsp = fastapi.post(
            f"/admin/technical_import?archive_name={zst_name}&target_project_id=0",
            headers=ADMIN_AUTH,
        )
        assert bad_rsp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        job = _run_technical_import(fastapi, zst_name, target_project_id=new_prj_id)
        assert job.state == "F", job
        assert job.result is not None
        assert job.result["project_id"] == new_prj_id

        # Old project ID must not exist
        old_prj_rsp = fastapi.get(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert old_prj_rsp.status_code == status.HTTP_404_NOT_FOUND

        # New project ID has all data and remapped partitioned IDs
        new_prj_rsp = fastapi.get(f"/projects/{new_prj_id}", headers=ADMIN_AUTH)
        assert new_prj_rsp.status_code == status.HTTP_200_OK
        assert new_prj_rsp.json()["title"] == "Technical move project"

        new_objs_rsp = fastapi.post(
            f"/object_set/{new_prj_id}/query",
            headers=ADMIN_AUTH,
            json={},
        )
        assert new_objs_rsp.status_code == status.HTTP_200_OK
        assert new_objs_rsp.json()["total_ids"] == expected_obj_count
        new_obj_ids = new_objs_rsp.json()["object_ids"]
        assert len(new_obj_ids) == expected_obj_count
        for oid in new_obj_ids:
            assert new_prj_id * OBJ_PRJ_OFFSET <= oid < (new_prj_id + 1) * OBJ_PRJ_OFFSET

        obj_rsp = fastapi.get(f"/object/{new_obj_ids[0]}", headers=ADMIN_AUTH)
        assert obj_rsp.status_code == status.HTTP_200_OK
        obj_data = obj_rsp.json()
        assert (
            new_prj_id * ACQ_PRJ_OFFSET
            <= obj_data["acquisid"]
            < (new_prj_id + 1) * ACQ_PRJ_OFFSET
        )
        assert (
            new_prj_id * SAM_PRJ_OFFSET
            <= obj_data["sample_id"]
            < (new_prj_id + 1) * SAM_PRJ_OFFSET
        )
    finally:
        zst_path.unlink(missing_ok=True)


def test_technical_import_regenerates_projectspriv_and_taxo_recast_ids(fastapi):
    from API_operations.helpers.Service import Service
    from DB.ProjectPrivilege import ProjectPrivilege
    from DB.TaxoRecast import RecastOperation, TaxoRecast
    from DB.helpers.ORM import select

    prj_id = do_test_import(fastapi, "Collision source project")

    with Service() as sce:
        sce.session.add(
            TaxoRecast(
                project_id=prj_id,
                operation=RecastOperation.project_export.value,
                transforms={"1": 2},
                documentation={"1": "recast doc"},
            )
        )
        sce.session.commit()
        src_priv_ids = list(
            sce.session.scalars(
                select(ProjectPrivilege.id).where(ProjectPrivilege.projid == prj_id)
            )
        )
        src_recast_ids = list(
            sce.session.scalars(
                select(TaxoRecast.recast_id).where(TaxoRecast.project_id == prj_id)
            )
        )
        assert len(src_priv_ids) >= 1
        assert len(src_recast_ids) == 1

    zst_bytes = _export_technical_archive(fastapi, prj_id)
    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)
    zst_name = f"test_tek_clone_{prj_id}.tar.zst"
    zst_path = user_root / zst_name
    zst_path.write_bytes(zst_bytes)

    new_prj_id = prj_id + 101
    try:
        # Import into new_prj_id while prj_id (with same projectspriv.id and taxo_recast.recast_id) still exists
        job = _run_technical_import(fastapi, zst_name, target_project_id=new_prj_id)
        assert job.state == "F", job
        assert job.result is not None
        assert job.result["project_id"] == new_prj_id
        assert job.result["tables"]["projectspriv"] == len(src_priv_ids)
        assert job.result["tables"]["taxo_recast"] == len(src_recast_ids)

        with Service() as sce:
            dst_priv_ids = list(
                sce.session.scalars(
                    select(ProjectPrivilege.id).where(
                        ProjectPrivilege.projid == new_prj_id
                    )
                )
            )
            dst_recasts = list(
                sce.session.scalars(
                    select(TaxoRecast).where(TaxoRecast.project_id == new_prj_id)
                )
            )
            assert len(dst_priv_ids) == len(src_priv_ids)
            assert set(dst_priv_ids).isdisjoint(src_priv_ids)
            assert len(dst_recasts) == len(src_recast_ids)
            assert {r.recast_id for r in dst_recasts}.isdisjoint(src_recast_ids)
            assert dst_recasts[0].transforms == {"1": 2}
    finally:
        zst_path.unlink(missing_ok=True)


def test_technical_import_skips_sequence_reset_for_empty_tables(fastapi):
    from sqlalchemy import text
    from API_operations.helpers.Service import Service

    prj_id = do_test_import(fastapi, "Empty images seq project")
    tar_bytes = zstd.decompress(_export_technical_archive(fastapi, prj_id))

    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)
    zst_name = f"test_tek_{prj_id}_no_images.tar.zst"
    zst_path = user_root / zst_name

    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as src_tf:
        with tarfile.open(name=zst_path, mode="w:zst") as dst_tf:
            for member in src_tf:
                if not member.isfile() or member.name.startswith("vault/"):
                    continue
                f = src_tf.extractfile(member)
                assert f is not None
                data = f.read()
                if member.name.endswith("_images.copy"):
                    data = b""
                ti = tarfile.TarInfo(name=member.name)
                ti.size = len(data)
                dst_tf.addfile(ti, BytesIO(data))

    sentinel_seq = 9_999_999
    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        with Service() as sce:
            sce.session.execute(
                text("SELECT setval('seq_images', :val, true)"),
                {"val": sentinel_seq},
            )
            sce.session.commit()

        job = _run_technical_import(fastapi, zst_name)
        assert job.state == "F", job
        assert job.result is not None
        assert job.result["tables"]["images"] == 0

        with Service() as sce:
            last_val = sce.session.execute(
                text("SELECT last_value FROM seq_images")
            ).scalar_one()
            assert last_val == sentinel_seq
    finally:
        zst_path.unlink(missing_ok=True)


def test_technical_import_never_lowers_sequences(fastapi):
    from sqlalchemy import text
    from API_operations.helpers.Service import Service

    prj_id = do_test_import(fastapi, "Keep higher seq project")
    zst_bytes = _export_technical_archive(fastapi, prj_id)

    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)
    zst_name = f"test_tek_{prj_id}_keep_seq.tar.zst"
    zst_path = user_root / zst_name
    zst_path.write_bytes(zst_bytes)

    sentinel_seq = 20_000_000
    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        with Service() as sce:
            sce.session.execute(
                text("SELECT setval('seq_images', :val, true)"),
                {"val": sentinel_seq},
            )
            sce.session.commit()

        job = _run_technical_import(fastapi, zst_name)
        assert job.state == "F", job
        assert job.result is not None
        assert job.result["tables"]["images"] > 0

        with Service() as sce:
            last_val = sce.session.execute(
                text("SELECT last_value FROM seq_images")
            ).scalar_one()
            assert last_val == sentinel_seq
    finally:
        zst_path.unlink(missing_ok=True)


def test_write_copy_stream_chunk_boundaries_and_maxsplit(monkeypatch):
    import BO.technical.TechImport as tech_import_mod
    from BO.technical.TechImport import TechnicalImport

    monkeypatch.setattr(tech_import_mod, "COPY_CHUNK_SIZE", 7)

    class _DummyCopy:
        def __init__(self) -> None:
            self.chunks: list[bytes] = []

        def write(self, data) -> None:
            assert isinstance(data, (bytes, bytearray))
            self.chunks.append(bytes(data))

    payload = b"10\t100\ta\tb\tc\n\\N\t250\tx\ty\tz\n30\t50\tu\tv\tw"
    copy = _DummyCopy()
    max_vals = TechnicalImport._write_copy_stream(
        copy,
        BytesIO(payload),
        transforms=[(0, lambda v: v if v == b"\\N" else b"%d" % (int(v) + 1000))],
        track_max_cols=[1],
    )
    assert max_vals == {1: 250}
    assert b"".join(copy.chunks) == (
        b"1010\t100\ta\tb\tc\n\\N\t250\tx\ty\tz\n1030\t50\tu\tv\tw"
    )


def test_reset_sequences_quotes_sequence_identifier():
    from BO.technical.TechImport import TechnicalImport

    class _FakeCursor:
        def __init__(self) -> None:
            self.queries: list[tuple[str, object]] = []
            self._results: list[object] = []

        def execute(self, query, params=None) -> None:
            if hasattr(query, "as_bytes"):
                sql = query.as_bytes().decode()
            else:
                sql = str(query)
            self.queries.append((sql, params))
            if "pg_catalog.pg_class" in sql:
                self._results.append(("public", "Seq With Space"))
            elif sql.startswith("SELECT last_value"):
                self._results.append((5, True))
            else:
                self._results.append(None)

        def fetchone(self):
            return self._results.pop(0)

    cur = _FakeCursor()
    TechnicalImport._reset_sequences(cur, {"public.Seq With Space": 10})
    # The sequence name must be rendered as a quoted identifier, never
    # interpolated as raw SQL.
    assert any('"public"."Seq With Space"' in sql for sql, _ in cur.queries)


def test_technical_import_commits_before_vault_extraction(fastapi, monkeypatch):
    from sqlalchemy import select
    from API_operations.helpers.Service import Service
    from BO.technical.TechImport import TechnicalImport
    from DB.Project import Project

    prj_id = do_test_import(fastapi, "Commit before vault project")
    zst_bytes = _export_technical_archive(fastapi, prj_id)

    user_root = UserFilesDirectory(ADMIN_USER_ID)._root_path
    user_root.mkdir(parents=True, exist_ok=True)
    zst_name = f"test_tek_{prj_id}_commit_before_vault.tar.zst"
    zst_path = user_root / zst_name
    zst_path.write_bytes(zst_bytes)

    orig_copy_vault_file = TechnicalImport._copy_vault_file
    checked_during_vault = []

    def _spy_copy_vault_file(self, rel_sub_path, src):
        if not checked_during_vault:
            with Service() as other_sce:
                visible_title = other_sce.session.execute(
                    select(Project.title).where(Project.projid == prj_id)
                ).scalar_one_or_none()
            checked_during_vault.append(visible_title)
        return orig_copy_vault_file(self, rel_sub_path, src)

    monkeypatch.setattr(TechnicalImport, "_copy_vault_file", _spy_copy_vault_file)

    try:
        del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
        assert del_rsp.status_code == status.HTTP_200_OK

        job = _run_technical_import(fastapi, zst_name)
        assert job.state == "F", job
        assert checked_during_vault == ["Commit before vault project"]
    finally:
        zst_path.unlink(missing_ok=True)


def test_dedup_progress_cb():
    from BO.technical.DumpConfig import dedup_progress_cb

    assert dedup_progress_cb(None) is None

    calls: list[tuple[int, str]] = []
    cb = dedup_progress_cb(lambda pct, msg: calls.append((pct, msg)))
    assert cb is not None

    cb(10, "Step A")
    cb(10, "Step A")
    cb(10, "Step B")
    cb(10, "Step B")
    cb(10, "Step A")
    cb(20, "Step A")

    assert calls == [
        (10, "Step A"),
        (10, "Step B"),
        (10, "Step A"),
        (20, "Step A"),
    ]


def test_technical_import_no_consecutive_duplicate_progress_cb(
    fastapi, tmp_path, monkeypatch
):
    from API_operations.helpers.Service import Service
    from BO.technical.TechImport import TechnicalImport

    prj_id = do_test_import(fastapi, "Dedup progress import project")
    zst_bytes = _export_technical_archive(fastapi, prj_id)
    archive_path = tmp_path / "export.tar.zst"
    archive_path.write_bytes(zst_bytes)

    del_rsp = fastapi.delete(f"/projects/{prj_id}", headers=ADMIN_AUTH)
    assert del_rsp.status_code == status.HTTP_200_OK

    monkeypatch.setattr(TechnicalImport, "IMAGES_REPORT_INTERVAL_SECONDS", 0.0)
    calls: list[tuple[int, str]] = []

    with Service() as sce:
        importer = TechnicalImport(sce.config.vault_dir())
        importer.import_project(
            archive_path,
            progress_start=1,
            progress_end=99,
            progress_cb=lambda pct, msg: calls.append((pct, msg)),
        )

    assert len(calls) > 0
    for prev, curr in zip(calls, calls[1:]):
        assert prev != curr
    vault_msgs = [msg for _, msg in calls if msg.startswith("Restored ")]
    assert len(vault_msgs) == len(set(vault_msgs))


def test_technical_import_disabled_by_config(fastapi, monkeypatch):
    from helpers.AppConfig import Config

    # Default when absent from config/env -> disabled (403 even for admin)
    monkeypatch.delenv("ENABLE_TECH_IMPORT", raising=False)
    monkeypatch.delitem(Config().parser, "ENABLE_TECH_IMPORT", raising=False)
    rsp = fastapi.post(
        "/admin/technical_import?archive_name=anything.tar.zst",
        headers=ADMIN_AUTH,
    )
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    assert rsp.json()["detail"] == "Technical import is disabled."

    # Explicitly set to false in env -> disabled
    monkeypatch.setenv("ENABLE_TECH_IMPORT", "false")
    rsp = fastapi.post(
        "/admin/technical_import?archive_name=anything.tar.zst",
        headers=ADMIN_AUTH,
    )
    assert rsp.status_code == status.HTTP_403_FORBIDDEN
    assert rsp.json()["detail"] == "Technical import is disabled."
