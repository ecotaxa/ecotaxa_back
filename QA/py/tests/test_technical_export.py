import compression.zstd as zstd
import json
import tarfile
from io import BytesIO

from starlette import status

from tests.api_wrappers import api_wait_for_stable_job
from tests.credentials import ADMIN_AUTH, USER_AUTH
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
        assert len(metadata["tables"]) == 24
        assert metadata["tables"][0]["name"] == "instrument"
        assert metadata["tables"][0]["copy_file"] == "01_instrument.copy"
        assert metadata["tables"][0]["primary_key"] == ["instrument_id"]
        projects_meta = next(t for t in metadata["tables"] if t["name"] == "projects")
        assert projects_meta["copy_file"] == "06_projects.copy"
        assert projects_meta["primary_key"] == ["projid"]
        assert any(c["name"] == "title" for c in projects_meta["columns"])
        obj_head_meta = next(t for t in metadata["tables"] if t["name"] == "obj_head")
        assert len(obj_head_meta["foreign_keys"]) > 0
        if expected_log is not None:
            assert expected_log in names
        for expected_copy in (
            "01_instrument.copy",
            "02_organizations.copy",
            "03_users.copy",
            "04_taxonomy.copy",
            "05_collection.copy",
            "06_projects.copy",
            "07_projectspriv.copy",
            "08_projects_taxo_stat.copy",
            "13_training.copy",
            "14_samples.copy",
            "15_acquisitions.copy",
            "16_process.copy",
            "17_obj_head.copy",
            "18_obj_field.copy",
            "19_images.copy",
            "23_prediction.copy",
            "24_prediction_histo.copy",
        ):
            assert expected_copy in names

        prj_member = tf.extractfile("06_projects.copy")
        assert prj_member is not None
        prj_copy = prj_member.read().decode("utf-8")
        assert str(prj_id) in prj_copy
        assert "Technical export project" in prj_copy

        users_member = tf.extractfile("03_users.copy")
        assert users_member is not None
        assert len(users_member.read()) > 0

        taxo_member = tf.extractfile("04_taxonomy.copy")
        assert taxo_member is not None
        assert len(taxo_member.read()) > 0

        from DB.Project import Project

        assert [c["name"] for c in projects_meta["columns"]] == [
            c.name for c in Project.__table__.columns
        ]

        restore_member = tf.extractfile("restore.sql")
        assert restore_member is not None
        restore_sql = restore_member.read().decode("utf-8")
        assert "\\copy instrument (" in restore_sql
        assert "FROM '01_instrument.copy'" in restore_sql
        assert "\\copy users (" in restore_sql
        assert "FROM '03_users.copy'" in restore_sql
        assert "\\copy taxonomy (" in restore_sql
        assert "FROM '04_taxonomy.copy'" in restore_sql
        assert "\\copy projects (" in restore_sql
        assert "FROM '06_projects.copy'" in restore_sql
        assert "\\copy prediction_histo (" in restore_sql
        assert "FROM '24_prediction_histo.copy'" in restore_sql

        vault_files = [n for n in names if n.startswith("vault/")]
        assert len(vault_files) > 0


def test_technical_export(fastapi):
    prj_id = do_test_import(fastapi, "Technical export project")

    # Non-authorized user cannot run technical export
    unauth_rsp = fastapi.post(
        f"/admin/technical_export?project_id={prj_id}", headers=USER_AUTH
    )
    assert unauth_rsp.status_code == status.HTTP_403_FORBIDDEN

    # Admin launches technical export job via endpoint
    rsp = fastapi.post(
        f"/admin/technical_export?project_id={prj_id}", headers=ADMIN_AUTH
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()

    job = api_wait_for_stable_job(fastapi, job_id)
    assert job.state == "F", job
    assert job.progress_pct == 100
    assert job.result["rowcount"] > 0
    assert job.result["tables"]["instrument"] >= 1
    assert job.result["tables"]["users"] >= 1
    assert job.result["tables"]["taxonomy"] >= 1
    assert job.result["tables"]["projects"] == 1
    assert job.result["tables"]["samples"] > 0
    assert job.result["tables"]["acquisitions"] > 0
    assert job.result["tables"]["process"] > 0
    assert job.result["tables"]["obj_head"] > 0
    assert job.result["tables"]["obj_field"] > 0
    assert job.result["tables"]["images"] > 0

    dl_rsp = fastapi.get(JOB_DOWNLOAD_URL.format(job_id=job_id), headers=ADMIN_AUTH)
    assert dl_rsp.status_code == status.HTTP_200_OK
    assert dl_rsp.headers["content-type"] == "application/zstd"
    assert f"export__TEK_{prj_id}_" in dl_rsp.headers["content-disposition"]
    assert ".tar.zst" in dl_rsp.headers["content-disposition"]
    _assert_technical_archive(dl_rsp.content, prj_id, expected_log=f"job_{job_id}.log")


def test_technical_export_no_idle_in_transaction_during_vault_copy(
    fastapi, tmp_path, monkeypatch
):
    import tarfile
    import time
    from sqlalchemy import text
    from API_operations.exports.Technical import Technical
    from BO.technical.TechDump import TechnicalDump

    prj_id = do_test_import(fastapi, "Technical export idle timeout project")

    orig_add = tarfile.TarFile.add

    def slow_vault_add(self, name, arcname=None, *args, **kwargs):
        if arcname and arcname.startswith("vault/"):
            time.sleep(0.35)
        return orig_add(self, name, arcname=arcname, *args, **kwargs)

    monkeypatch.setattr(tarfile.TarFile, "add", slow_vault_add)

    with Technical(prj_id) as sce:
        from DB.helpers.Connection import Connection

        orig_get_raw = Connection.get_raw_psycopg_connection
        raw_conn_calls = []

        def _get_raw_with_timeout(read_only: bool = False, **kwargs):
            raw_conn_calls.append((read_only, kwargs.get("isolation_level")))
            conn = orig_get_raw(read_only=read_only, **kwargs)
            conn.execute("SET SESSION idle_in_transaction_session_timeout = '200ms'")
            conn.commit()
            return conn

        monkeypatch.setattr(
            Connection,
            "get_raw_psycopg_connection",
            staticmethod(_get_raw_with_timeout),
        )
        dumper = TechnicalDump(prj_id, sce.config.vault_dir())
        archive_path = tmp_path / "export.tar.zst"
        dumper.dump_project(archive_path)
        assert sce.ro_session.execute(text("SELECT 1")).scalar() == 1
        # The whole dump (tables, metadata and vault image list) must be read
        # from a single consistent snapshot.
        from psycopg import IsolationLevel

        assert raw_conn_calls == [(True, IsolationLevel.REPEATABLE_READ)]


def test_technical_export_no_consecutive_duplicate_progress_cb(
    fastapi, tmp_path, monkeypatch
):
    from API_operations.exports.Technical import Technical
    from BO.technical.TechDump import TechnicalDump

    prj_id = do_test_import(fastapi, "Dedup progress export project")
    monkeypatch.setattr(TechnicalDump, "IMAGES_REPORT_INTERVAL_SECONDS", 0.0)
    calls: list[tuple[int, str]] = []

    with Technical(prj_id) as sce:
        dumper = TechnicalDump(prj_id, sce.config.vault_dir())
        archive_path = tmp_path / "export.tar.zst"
        dumper.dump_project(
            archive_path,
            progress_start=1,
            progress_end=99,
            progress_cb=lambda pct, msg: calls.append((pct, msg)),
        )

    assert len(calls) > 0
    for prev, curr in zip(calls, calls[1:]):
        assert prev != curr
    assert sum(1 for pct, _ in calls if pct == 99) == 1
