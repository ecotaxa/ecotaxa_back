import logging

from API_models.imports import ImportReq, ImportRsp
from API_operations.AsciiDump import AsciiDumper
from API_operations.CRUD.Jobs import JobCRUDService
from API_operations.imports.Import import FileImport
from DB.Job import DBJobStateEnum

from tests.credentials import ADMIN_USER_ID
from tests.jobs import wait_for_stable, check_job_ok
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


def test_import_update(fastapi, caplog, tstlogs):
    """Update TSVs"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Import update")

    # Plain import first
    import_plain(fastapi, prj_id)
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "before_upd.txt")

    # Update using initial import data, should do nothing
    do_import_update(prj_id, caplog, "Yes", str(PLAIN_DIR))
    print("Import update 0:" + "\n".join(caplog.messages))
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == []

    # Update without classif, 10 cells
    do_import_update(prj_id, caplog, "Yes", str(UPDATE_DIR))
    print("Import update 1:" + "\n".join(caplog.messages))
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # 9 fields + 7 derived sun positions
    assert nb_upds == 16
    saves = [msg for msg in caplog.messages if "Batch save objects" in msg]
    assert saves == ["Batch save objects of 0/0/0/0/0/0"] * 4

    # Update classif, 2 cells, one classif ID and one classif quality
    do_import_update(prj_id, caplog, "Cla", str(UPDATE_DIR))
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    print("Import update 2:" + "\n".join(caplog.messages))
    assert nb_upds == 2
    # 1 line corresponds to nothing, on purpose
    nb_notfound = len(
        [msg for msg in caplog.messages if "not found while updating" in msg]
    )
    assert nb_notfound == 3
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd.txt")
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    # ecotaxa/ecotaxa_dev#583: Check that no image was added during the update
    saves = [msg for msg in caplog.messages if "Batch save objects" in msg]
    assert saves == ["Batch save objects of 0/0/0/0/0/0"] * 4

    # Update classif, no change -> No log line
    do_import_update(prj_id, caplog, "Yes", str(UPDATE_DIR))
    print("Import update 3:" + "\n".join(caplog.messages))
    assert len(caplog.messages) > 0
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == []
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd_3.txt")


def test_import_update_sample_meta(fastapi, caplog, tstlogs):
    """Update TSV has a != free col sample_tot_vol"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Import update sample meta")

    # Plain import first
    do_import(prj_id, IMPORT_TOT_VOL, ADMIN_USER_ID)
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "before_upd_tot_vol.txt")

    # Update using initial import data, should do nothing
    do_import_update(prj_id, caplog, "Yes", str(IMPORT_TOT_VOL))
    print("Import update 0:" + "\n".join(caplog.messages))
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == []

    do_import_update(prj_id, caplog, "Yes", str(IMPORT_TOT_VOL_UPDATE))
    print("Import update 1:" + "\n".join(caplog.messages))
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == [
        "Updating samples 'm106_mn01_n1_sml' using [('t05', \"'999999'->'5.75'\")]"
    ]

    do_import_update(
        prj_id, caplog, "Yes", str(IMPORT_TOT_VOL_BAD_UPDATE), expected_errors=True
    )
    print("Import update 2:" + "\n".join(caplog.messages))
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    # Process IDs are not unique nor structural anymore, feel free to update
    assert upds == [
        "Updating process 'zooprocess_m106_mn01_n1_sml_typo' using [('orig_id', \"'zooprocess_m106_mn01_n1_sml'->'zooprocess_m106_mn01_n1_sml_typo'\")]",
        "Updating process 'zooprocess_m106_mn01_n1_sml' using [('orig_id', \"'zooprocess_m106_mn01_n1_sml_typo'->'zooprocess_m106_mn01_n1_sml'\")]",
    ]
    errs = [
        a_msg.getMessage()
        for a_msg in caplog.records
        if a_msg.levelno == logging.WARNING and a_msg.getMessage().startswith("Invalid")
    ]
    assert errs == [
        "Invalid acq_id value 'generic_m106_mn01_n1_sml_typo'. Your TSV is inconsistent.",
        "Invalid sample_id value 'm106_mn01_n1_sml_typo'. Your TSV is inconsistent.",
    ]


def test_import_update_various(fastapi, caplog, tstlogs):
    """Update TSVs"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Import update various")

    # Plain import first
    import_various(fastapi, prj_id)
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "before_upd.txt")

    # Update using initial import data, should do nothing
    do_import_update(prj_id, caplog, "Yes", str(VARIOUS_STATES_DIR))
    print("Import update 0:" + "\n".join(caplog.messages))
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == []

    # Update without classif, 10 cells
    do_import_update(prj_id, caplog, "Yes", str(UPDATE_DIR))
    print("Import update various 1:" + "\n".join(caplog.messages))
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # 9 fields + 7 derived sun positions - 3 different objects
    assert nb_upds == 14
    saves = [msg for msg in caplog.messages if "Batch save objects" in msg]
    assert saves == ["Batch save objects of 0/0/0/0/0/0"] * 4

    # Update classif, 2 cells, one classif ID and one classif quality + one fresh object to predicted
    do_import_update(prj_id, caplog, "Cla", str(UPDATE_DIR))
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    print("Import update various 2:" + "\n".join(caplog.messages))
    assert nb_upds == 5
    nb_notfound = len(
        [msg for msg in caplog.messages if "not found while updating" in msg]
    )
    assert nb_notfound == 5
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd.txt")
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    # ecotaxa/ecotaxa_dev#583: Check that no image was added during the update
    saves = [msg for msg in caplog.messages if "Batch save objects" in msg]
    assert saves == ["Batch save objects of 0/0/0/0/0/0"] * 4

    # Update classif, no change -> No log line
    do_import_update(prj_id, caplog, "Yes", str(UPDATE_DIR))
    print("Import update 3:" + "\n".join(caplog.messages))
    assert len(caplog.messages) > 0
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == []
    with AsciiDumper() as dump_sce:
        dump_sce.run(projid=prj_id, out=tstlogs / "after_upd_3.txt")


def do_import_update(prj_id, caplog, mode, source, expected_errors=False):
    params = ImportReq(skip_existing_objects=True, update_mode=mode, source_path=source)
    caplog.clear()
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)

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
        with JobCRUDService() as sce:
            sce.reply(ADMIN_USER_ID, rsp.job_id, reply)
        job = wait_for_stable(rsp.job_id)
    check_job_ok(job)
    # Check that all went fine
    if not expected_errors:
        for a_msg in caplog.records:
            assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    # #498: No extra parent should be created
    for a_msg in caplog.records:
        assert "++ ID" not in a_msg.getMessage()
