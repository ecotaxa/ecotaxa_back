import compression.zstd as zstd
import json
import tarfile
from io import BytesIO

from starlette import status

from API_operations.exports.Technical import Technical as TechnicalExport
from tests.api_wrappers import api_wait_for_stable_job
from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID, USER_AUTH
from tests.export_shared import JOB_DOWNLOAD_URL
from tests.test_import import do_test_import


def _count_zstd_frames(content: bytes) -> int:
    offset = 0
    frames = 0
    while offset < len(content):
        offset += zstd.get_frame_size(memoryview(content)[offset:])
        frames += 1
    return frames


def _assert_technical_archive(
    content: bytes, prj_id: int, expected_log: str | None = None
):
    assert _count_zstd_frames(content) == 2
    with tarfile.open(fileobj=BytesIO(content), mode="r:zst") as tf:
        ordered_names = tf.getnames()
        assert ordered_names[0] == "0_metadata.json"
        names = set(ordered_names)
        assert "restore.sql" in names

        meta_member = tf.extractfile("0_metadata.json")
        assert meta_member is not None
        metadata = json.loads(meta_member.read().decode("utf-8"))
        assert metadata["project_id"] == prj_id
        assert metadata["format"] == "pg_copy_tar_zst"
        assert metadata["postgres_version"]
        assert len(metadata["tables"]) == 19
        assert metadata["tables"][0]["name"] == "projects"
        assert metadata["tables"][0]["copy_file"] == "01_projects.copy"
        assert metadata["tables"][0]["primary_key"] == ["projid"]
        assert any(c["name"] == "title" for c in metadata["tables"][0]["columns"])
        obj_head_meta = next(t for t in metadata["tables"] if t["name"] == "obj_head")
        assert len(obj_head_meta["foreign_keys"]) > 0
        if expected_log is not None:
            assert expected_log in names
        for expected_copy in (
            "01_projects.copy",
            "02_projectspriv.copy",
            "03_projects_taxo_stat.copy",
            "08_training.copy",
            "09_samples.copy",
            "10_acquisitions.copy",
            "11_process.copy",
            "12_obj_head.copy",
            "13_obj_field.copy",
            "14_images.copy",
            "18_prediction.copy",
            "19_prediction_histo.copy",
        ):
            assert expected_copy in names

        prj_member = tf.extractfile("01_projects.copy")
        assert prj_member is not None
        prj_copy = prj_member.read().decode("utf-8")
        assert str(prj_id) in prj_copy
        assert "Technical export project" in prj_copy

        restore_member = tf.extractfile("restore.sql")
        assert restore_member is not None
        restore_sql = restore_member.read().decode("utf-8")
        assert "\\copy projects FROM '01_projects.copy'" in restore_sql
        assert "\\copy prediction_histo FROM '19_prediction_histo.copy'" in restore_sql

        vault_files = [n for n in names if n.startswith("vault/")]
        assert len(vault_files) > 0


def test_technical_export(fastapi):
    prj_id = do_test_import(fastapi, "Technical export project")

    # Non-authorized user cannot run technical export
    unauth_rsp = fastapi.get(
        f"/admin/technical_export?project_id={prj_id}", headers=USER_AUTH
    )
    assert unauth_rsp.status_code == status.HTTP_403_FORBIDDEN

    # Admin streams technical export archive directly from endpoint
    rsp = fastapi.get(
        f"/admin/technical_export?project_id={prj_id}", headers=ADMIN_AUTH
    )
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.headers["content-type"] == "application/zstd"
    assert f"export__TEK_{prj_id}_" in rsp.headers["content-disposition"]
    assert ".tar.zst" in rsp.headers["content-disposition"]
    _assert_technical_archive(rsp.content, prj_id)

    # Background job still uses the same extraction logic
    with TechnicalExport(project_id=prj_id) as sce:
        job_rsp = sce.run(ADMIN_USER_ID)
    job_id = job_rsp.job_id

    job = api_wait_for_stable_job(fastapi, job_id)
    assert job.state == "F", job
    assert job.progress_pct == 100
    assert job.result["rowcount"] > 0
    assert job.result["tables"]["projects"] == 1
    assert job.result["tables"]["samples"] > 0
    assert job.result["tables"]["acquisitions"] > 0
    assert job.result["tables"]["process"] > 0
    assert job.result["tables"]["obj_head"] > 0
    assert job.result["tables"]["obj_field"] > 0
    assert job.result["tables"]["images"] > 0

    dl_rsp = fastapi.get(JOB_DOWNLOAD_URL.format(job_id=job_id), headers=ADMIN_AUTH)
    assert dl_rsp.status_code == status.HTTP_200_OK
    _assert_technical_archive(dl_rsp.content, prj_id, expected_log=f"job_{job_id}.log")
