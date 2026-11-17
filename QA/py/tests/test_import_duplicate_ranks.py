# -*- coding: utf-8 -*-
import shutil
from pathlib import Path
from PIL import Image as PILImage

from tests.api_wrappers import api_file_import, api_wait_for_stable_job
from tests.consts import SHARED_DIR
from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID
from tests.jobs import check_job_ok, check_job_errors
from tests.test_import import create_project


def _create_dummy_image(path: Path):
    img = PILImage.new("RGB", (10, 10), color=(128, 128, 128))
    img.save(path)


def test_import_duplicate_rank_in_same_tsv(fastapi, tmp_path):
    """
    Validation must fail when the same TSV contains multiple images for the same object
    with the same img_rank.
    """
    import_dir = SHARED_DIR / "import_test_dup_rank_same_tsv"
    if import_dir.exists():
        shutil.rmtree(import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)

    try:
        _create_dummy_image(import_dir / "img1.jpg")
        _create_dummy_image(import_dir / "img2.jpg")

        tsv_content = (
            "img_file_name\tobject_id\timg_rank\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[f]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img1.jpg\tobj_dup_rank\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
            "img2.jpg\tobj_dup_rank\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (import_dir / "ecotaxa_test.tsv").write_text(tsv_content)

        prj_id = create_project(ADMIN_USER_ID, "Test Duplicate Rank In TSV")
        params = dict(
            source_path="import_test_dup_rank_same_tsv", skip_existing_objects=False
        )
        rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
        job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
        errors = check_job_errors(job)

        expected_error = (
            "line 4: (Object 'obj_dup_rank', Rank 0) is already in this TSV."
        )
        assert any(
            expected_error in err for err in errors
        ), f"Expected error not found in: {errors}"
    finally:
        if import_dir.exists():
            shutil.rmtree(import_dir)


def test_import_duplicate_rank_against_existing_db(fastapi):
    """
    Validation must fail when importing a new image with an (object_id, img_rank)
    that already exists in the project.
    """
    dir1 = SHARED_DIR / "import_test_dup_rank_db_1"
    dir2 = SHARED_DIR / "import_test_dup_rank_db_2"
    for d in (dir1, dir2):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    try:
        # First import: obj_existing with rank 0
        _create_dummy_image(dir1 / "img1.jpg")
        tsv1 = (
            "img_file_name\tobject_id\timg_rank\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[f]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img1.jpg\tobj_existing\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (dir1 / "ecotaxa_test.tsv").write_text(tsv1)

        prj_id = create_project(ADMIN_USER_ID, "Test Duplicate Rank Against DB")
        params1 = dict(
            source_path="import_test_dup_rank_db_1", skip_existing_objects=False
        )
        rsp1 = api_file_import(fastapi, prj_id, params1, ADMIN_AUTH)
        job1 = api_wait_for_stable_job(fastapi, rsp1.json()["job_id"])
        check_job_ok(job1)

        # Second import: same obj_existing, different image file img2.jpg, but same rank 0
        _create_dummy_image(dir2 / "img2.jpg")
        tsv2 = (
            "img_file_name\tobject_id\timg_rank\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[f]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img2.jpg\tobj_existing\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (dir2 / "ecotaxa_test.tsv").write_text(tsv2)

        params2 = dict(
            source_path="import_test_dup_rank_db_2", skip_existing_objects=False
        )
        rsp2 = api_file_import(fastapi, prj_id, params2, ADMIN_AUTH)
        job2 = api_wait_for_stable_job(fastapi, rsp2.json()["job_id"])
        errors = check_job_errors(job2)

        expected_error = (
            "(Object 'obj_existing', Rank 0) is already in EcoTaxa or being imported."
        )
        assert any(
            expected_error in err for err in errors
        ), f"Expected error not found in: {errors}"
    finally:
        for d in (dir1, dir2):
            if d.exists():
                shutil.rmtree(d)


def test_import_distinct_ranks_same_object(fastapi):
    """
    Importing multiple images for the same object with different ranks (0, 1) must succeed.
    """
    import_dir = SHARED_DIR / "import_test_distinct_ranks"
    if import_dir.exists():
        shutil.rmtree(import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)

    try:
        _create_dummy_image(import_dir / "img1.jpg")
        _create_dummy_image(import_dir / "img2.jpg")

        tsv_content = (
            "img_file_name\tobject_id\timg_rank\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[f]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img1.jpg\tobj_distinct_rank\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
            "img2.jpg\tobj_distinct_rank\t1\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (import_dir / "ecotaxa_test.tsv").write_text(tsv_content)

        prj_id = create_project(ADMIN_USER_ID, "Test Distinct Ranks Same Object")
        params = dict(
            source_path="import_test_distinct_ranks", skip_existing_objects=False
        )
        rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
        job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
        check_job_ok(job)
        assert job.result["rowcount"] == 2
    finally:
        if import_dir.exists():
            shutil.rmtree(import_dir)


def test_import_auto_assigned_ranks_same_object(fastapi):
    """
    Importing multiple images for the same object without img_rank must auto-assign
    distinct ranks (0, 1) and succeed.
    """
    import_dir = SHARED_DIR / "import_test_auto_ranks"
    if import_dir.exists():
        shutil.rmtree(import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)

    try:
        _create_dummy_image(import_dir / "img1.jpg")
        _create_dummy_image(import_dir / "img2.jpg")

        tsv_content = (
            "img_file_name\tobject_id\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img1.jpg\tobj_auto_rank\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
            "img2.jpg\tobj_auto_rank\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (import_dir / "ecotaxa_test.tsv").write_text(tsv_content)

        prj_id = create_project(ADMIN_USER_ID, "Test Auto Ranks Same Object")
        params = dict(source_path="import_test_auto_ranks", skip_existing_objects=False)
        rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
        job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
        check_job_ok(job)
        assert job.result["rowcount"] == 2
    finally:
        if import_dir.exists():
            shutil.rmtree(import_dir)


def test_import_mixed_explicit_and_implicit_ranks(fastapi):
    """
    Importing an object with one explicit rank (e.g. 0) and one omitted rank
    should automatically compute the next available rank (1) and succeed without conflict.
    """
    import_dir = SHARED_DIR / "import_test_mixed_ranks"
    if import_dir.exists():
        shutil.rmtree(import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)

    try:
        _create_dummy_image(import_dir / "img1.jpg")
        _create_dummy_image(import_dir / "img2.jpg")

        tsv_content = (
            "img_file_name\tobject_id\timg_rank\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[f]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img1.jpg\tobj_mixed_rank\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
            "img2.jpg\tobj_mixed_rank\t\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (import_dir / "ecotaxa_test.tsv").write_text(tsv_content)

        prj_id = create_project(ADMIN_USER_ID, "Test Mixed Ranks Same Object")
        params = dict(
            source_path="import_test_mixed_ranks", skip_existing_objects=False
        )
        rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
        job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
        check_job_ok(job)
        assert job.result["rowcount"] == 2
    finally:
        if import_dir.exists():
            shutil.rmtree(import_dir)


def test_import_duplicate_rank_skipped_when_skip_existing_objects(fastapi):
    """
    When skip_existing_objects=True, re-importing existing object/image/rank entries
    are ignored (skipped) rather than causing an import validation error.
    """
    dir1 = SHARED_DIR / "import_test_skip_rank_db_1"
    dir2 = SHARED_DIR / "import_test_skip_rank_db_2"
    for d in (dir1, dir2):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    try:
        # First import
        _create_dummy_image(dir1 / "img1.jpg")
        tsv1 = (
            "img_file_name\tobject_id\timg_rank\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[f]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img1.jpg\tobj_skip_dup\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (dir1 / "ecotaxa_test.tsv").write_text(tsv1)

        prj_id = create_project(ADMIN_USER_ID, "Test Skip Existing Duplicate Rank")
        params1 = dict(
            source_path="import_test_skip_rank_db_1", skip_existing_objects=False
        )
        rsp1 = api_file_import(fastapi, prj_id, params1, ADMIN_AUTH)
        job1 = api_wait_for_stable_job(fastapi, rsp1.json()["job_id"])
        check_job_ok(job1)

        # Second import: re-importing same object and image with skip_existing_objects=True
        _create_dummy_image(dir2 / "img1.jpg")
        tsv2 = (
            "img_file_name\tobject_id\timg_rank\tsample_id\tacq_id\tobject_lat\tobject_lon\tobject_date\tobject_time\n"
            "[t]\t[t]\t[f]\t[t]\t[t]\t[f]\t[f]\t[f]\t[f]\n"
            "img1.jpg\tobj_skip_dup\t0\tsmp1\tacq1\t10.0\t20.0\t20200101\t120000\n"
        )
        (dir2 / "ecotaxa_test.tsv").write_text(tsv2)

        params2 = dict(
            source_path="import_test_skip_rank_db_2", skip_existing_objects=True
        )
        rsp2 = api_file_import(fastapi, prj_id, params2, ADMIN_AUTH)
        job2 = api_wait_for_stable_job(fastapi, rsp2.json()["job_id"])
        check_job_ok(job2)
    finally:
        for d in (dir1, dir2):
            if d.exists():
                shutil.rmtree(d)
