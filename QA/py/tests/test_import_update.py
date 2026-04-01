import asyncio
import logging
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
from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH
from tests.jobs import check_job_ok, api_reply_to_waiting_job
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
    assert len(saves) == 4
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
    assert len(saves) == 4
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
