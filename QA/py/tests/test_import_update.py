import asyncio
import logging
import shutil
import time
from types import SimpleNamespace

import pytest
from API_operations.AsciiDump import AsciiDumper
from DB.Job import DBJobStateEnum

from tests.api_wrappers import (
    api_wait_for_stable_job,
    api_file_import,
    api_get_log_file,
)
from tests.consts import SHARED_DIR
from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH
from tests.jobs import check_job_ok, check_job_errors, api_reply_to_waiting_job
from tests.test_import import (
    create_project,
    UPDATE_DIR,
    VARIOUS_STATES_DIR,
    import_various,
    import_plain,
    PLAIN_DIR,
    IMPORT_TOT_VOL,
    do_import,
    IMPORT_TOT_VOL_UPDATE,
    IMPORT_TOT_VOL_BAD_UPDATE,
)

# A TSV-only source (no enclosing directory): imports as a "lone file"
LONE_OK_TSV = (
    SHARED_DIR / "import_update" / "m106_mn01_n1_sml" / "ecotaxa_m106_mn01_n1_sml.tsv"
)
# Same, but referencing images which won't sit next to it -> validation fails
LONE_KO_TSV = (
    SHARED_DIR / "import_test" / "m106_mn01_n1_sml" / "ecotaxa_m106_mn01_n1_sml.tsv"
)


# @pytest.mark.asyncio
def test_import_update(fastapi, caplog, tstlogs):
    """Update TSVs"""
    prj_id = create_project(ADMIN_USER_ID, "Test Import update")

    # Plain import first
    import_plain(fastapi, prj_id)
    # await asyncio.sleep(0.05)
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "before_upd.txt")

    # Update using initial import data, should do nothing
    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(PLAIN_DIR))
    # await asyncio.sleep(0.05)
    # print("Import update 0:" + "\n".join(caplog.messages))
    upds = [line for line in log if "Updating" in line]
    assert upds == []

    # Update without classif, 10 cells
    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(UPDATE_DIR))
    # print(f"Logging Lock State: {logging._lock._owner}")
    # await asyncio.sleep(0.05)
    # print("Import update 1:" + "\n".join(caplog.messages))
    nb_upds = len([line for line in log if "Updating" in line])
    # 9 fields + 7 derived sun positions
    assert nb_upds == 16
    saves = [line for line in log if "Batch save objects" in line]
    assert len(saves) == 4  # Note: Is only 2 with spawned tasks
    for s in saves:
        assert "Batch save objects of 0/0/0/0/0/0" in s

    # Update classif, 2 cells, one classif ID and one classif quality
    log = do_import_update(fastapi, prj_id, caplog, "Cla", str(UPDATE_DIR))
    # print(f"Logging Lock State: {logging._lock._owner}")
    nb_upds = len([line for line in log if "Updating" in line])
    assert nb_upds == 2
    # 1 line corresponds to nothing, on purpose
    nb_notfound = len([line for line in log if "not found while updating" in line])
    assert nb_notfound == 3
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd.txt")
    # ecotaxa/ecotaxa_dev#583: Check that no image was added during the update
    saves = [line for line in log if "Batch save objects" in line]
    assert len(saves) == 4  # Note: Is only 2 with spawned tasks
    for s in saves:
        assert "Batch save objects of 0/0/0/0/0/0" in s

    # Update classif, no change -> No log line
    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(UPDATE_DIR))
    # print("Import update 3:" + "\n".join(caplog.messages))
    upds = [line for line in log if "Updating" in line]
    assert upds == []
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd_3.txt")


def test_import_update_sample_meta(fastapi, caplog, tstlogs):
    """Update TSV has a != free col sample_tot_vol"""
    prj_id = create_project(ADMIN_USER_ID, "Test Import update sample meta")

    # Plain import first
    do_import(fastapi, prj_id, IMPORT_TOT_VOL, ADMIN_AUTH)
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "before_upd_tot_vol.txt")

    # Update using initial import data, should do nothing
    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(IMPORT_TOT_VOL))
    print("Import update 0:" + str(log))
    upds = [line for line in log if "Updating" in line]
    assert upds == []

    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(IMPORT_TOT_VOL_UPDATE))
    print("Import update 1:" + str(log))
    upds = [line for line in log if "Updating" in line]
    assert any(
        "Updating samples 'm106_mn01_n1_sml' using [('t05', \"'999999'->'5.75'\")]"
        in line
        for line in upds
    )

    log = do_import_update(
        fastapi,
        prj_id,
        caplog,
        "Yes",
        str(IMPORT_TOT_VOL_BAD_UPDATE),
        expected_errors=True,
    )
    print("Import update 2:" + str(log))
    upds = [line for line in log if "Updating" in line]
    # Process IDs are not unique nor structural anymore, feel free to update
    assert any(
        "Updating process 'zooprocess_m106_mn01_n1_sml_typo' using [('orig_id', \"'zooprocess_m106_mn01_n1_sml'->'zooprocess_m106_mn01_n1_sml_typo'\")]"
        in line
        for line in upds
    )
    assert any(
        "Updating process 'zooprocess_m106_mn01_n1_sml' using [('orig_id', \"'zooprocess_m106_mn01_n1_sml_typo'->'zooprocess_m106_mn01_n1_sml'\")]"
        in line
        for line in upds
    )
    errs = [line for line in log if "WARNING" in line and "Invalid" in line]
    assert len(errs) == 2


def test_import_update_various(fastapi, caplog, tstlogs):
    """Update TSVs"""
    prj_id = create_project(ADMIN_USER_ID, "Test Import update various")

    # Plain import first
    import_various(fastapi, prj_id)
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "before_upd.txt")

    # Update using initial import data, should do nothing
    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(VARIOUS_STATES_DIR))
    print("Import update 0:" + str(log))
    upds = [line for line in log if "Updating" in line]
    assert upds == []

    # Update without classif, 10 cells
    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(UPDATE_DIR))
    print("Import update various 1:" + str(log))
    nb_upds = len([line for line in log if "Updating" in line])
    # 9 fields + 7 derived sun positions - 3 different objects
    assert nb_upds == 14
    saves = [line for line in log if "Batch save objects" in line]
    assert len(saves) == 4
    for s in saves:
        assert "Batch save objects of 0/0/0/0/0/0" in s

    # Update classif, 2 cells, one classif ID and one classif quality + one fresh object to predicted
    log = do_import_update(fastapi, prj_id, caplog, "Cla", str(UPDATE_DIR))
    nb_upds = len([line for line in log if "Updating" in line])
    print("Import update various 2:" + str(log))
    assert nb_upds == 5
    nb_notfound = len([line for line in log if "not found while updating" in line])
    assert nb_notfound == 5
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd.txt")
    # ecotaxa/ecotaxa_dev#583: Check that no image was added during the update
    saves = [line for line in log if "Batch save objects" in line]
    assert len(saves) == 4
    for s in saves:
        assert "Batch save objects of 0/0/0/0/0/0" in s

    # Update classif, no change -> No log line
    log = do_import_update(fastapi, prj_id, caplog, "Yes", str(UPDATE_DIR))
    print("Import update 3:" + str(log))
    upds = [line for line in log if "Updating" in line]
    assert upds == []
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd_3.txt")


def do_import_update(fastapi, prj_id, caplog, mode, source, expected_errors=False):
    params = dict(skip_existing_objects=True, update_mode=mode, source_path=source)
    caplog.clear()
    caplog.set_level(logging.INFO)
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job_id = rsp.json()["job_id"]
    job = api_wait_for_stable_job(fastapi, job_id)

    if job.state == DBJobStateEnum.Asking:
        usr_label_to_id = {"admin4test": 1, "elizandro rodriguez": 1}  # Map to admin
        taxa_label_to_id = {
            "other": 99999,
            "ozzeur": 85011,
        }  # 'other<dead'  # 'other<living'
        reply = {"users": {}, "taxa": {}}
        for usr in job.question["missing_users"]:
            reply["users"][usr] = usr_label_to_id[usr]
        for txo in job.question["missing_taxa"]:
            reply["taxa"][txo] = taxa_label_to_id[txo]
        api_reply_to_waiting_job(fastapi, job_id, reply)
        job = api_wait_for_stable_job(fastapi, job_id)
    check_job_ok(job)
    log = api_get_log_file(fastapi, job.id)
    # Check that all went fine
    if not expected_errors:
        assert all(":ERROR" not in line for line in log)
    return log


def test_import_lone_tsv_ok(fastapi, caplog):
    """A single TSV file (not a directory) can be imported: it is moved into a
    dedicated temporary directory for the run, which is dropped once the job is OK.
    """
    prj_id = create_project(ADMIN_USER_ID, "Test import lone TSV OK")
    # Need existing objects to update
    import_plain(fastapi, prj_id)

    # A throwaway copy, sitting alone (no enclosing directory) in the common folder
    lone_name = "ecotaxa_lone_ok_%d.tsv" % prj_id
    lone_abs = SHARED_DIR / lone_name
    shutil.copyfile(LONE_OK_TSV, lone_abs)
    try:
        log = do_import_update(fastapi, prj_id, caplog, "Yes", lone_name)
        # The lone file was relocated then removed along with its temp directory
        assert not lone_abs.exists()
        assert any("Lone file import" in line for line in log)
    finally:
        if lone_abs.exists():
            lone_abs.unlink()


def test_import_lone_tsv_ko_restores_file(fastapi):
    """When the job fails, the lone input file is put back where it was."""
    prj_id = create_project(ADMIN_USER_ID, "Test import lone TSV KO")

    lone_name = "ecotaxa_lone_ko_%d.tsv" % prj_id
    lone_abs = SHARED_DIR / lone_name
    shutil.copyfile(LONE_KO_TSV, lone_abs)
    original_bytes = lone_abs.read_bytes()
    try:
        # Plain mode: the TSV references images which are not next to it -> errors
        params = dict(source_path=lone_name)
        rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
        job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
        errors = check_job_errors(job)
        assert any("Missing Image" in an_err for an_err in errors)
        # The file has been moved back to its initial location, untouched
        assert lone_abs.exists()
        assert lone_abs.read_bytes() == original_bytes
    finally:
        if lone_abs.exists():
            lone_abs.unlink()
