# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
import time
from os.path import dirname, realpath
from pathlib import Path

import pytest
from API_models.crud import *

# noinspection PyPackageRequirements
from API_models.imports import *

# noinspection PyPackageRequirements
from API_operations.AsciiDump import AsciiDumper

# noinspection PyPackageRequirements
from API_operations.CRUD.Jobs import JobCRUDService

# Import services
# noinspection PyPackageRequirements
from API_operations.CRUD.Projects import ProjectsService
from API_operations.JsonDumper import JsonDumper

# noinspection PyPackageRequirements
from API_operations.imports.Import import FileImport
from DB.Job import DBJobStateEnum
from starlette import status

from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID
from tests.jobs import (
    wait_for_stable,
    check_job_ok,
    check_job_errors,
    get_job_errors,
    api_wait_for_stable_job,
    api_check_job_questions,
    api_reply_to_waiting_job,
)
from tests.prj_utils import check_project

# All files paths are now relative to root shared directory
TEST_DIR = Path(dirname(realpath(__file__))).resolve()
SHARED_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
FTP_DIR = SHARED_DIR / "ftp"
DATA_DIR = Path("")
PLAIN_FILE = DATA_DIR / "import_test.zip"  # As seen from server
PLAIN_FILE_PATH = SHARED_DIR / "import_test.zip"  # As seen from client
V6_FILE = DATA_DIR / "UVP6_example.zip"
V6_DIR = DATA_DIR / "import_uvp6_zip_in_dir"
PLAIN_DIR = DATA_DIR / "import_test"
UPDATE_DIR = DATA_DIR / "import_update"
BAD_FREE_DIR = DATA_DIR / "import_bad_free_data"
SPARSE_DIR = DATA_DIR / "import_sparse"
PLUS_DIR = DATA_DIR / "import_test_plus"
JUST_PREDICTED_DIR = DATA_DIR / "import_just_predicted"
WEIRD_DIR = DATA_DIR / "import_test_weird"
ISSUES_DIR = DATA_DIR / "import_issues" / "tsv_issues"
ISSUES_DIR2 = DATA_DIR / "import_issues" / "no_classif_id"
ISSUES_DIR3 = DATA_DIR / "import_issues" / "tsv_too_many_cols"
ISSUES_DIR4 = DATA_DIR / "import_issues" / "duplicate_in_tsv"
ISSUES_DIR5 = DATA_DIR / "import_issues" / "predicted_but_what"
MIX_OF_STATES = DATA_DIR / "import_mixed_states"
EMPTY_DIR = DATA_DIR / "import_issues" / "no_relevant_file"
EMPTY_TSV_DIR = DATA_DIR / "import_issues" / "empty_tsv"
EMPTY_TSV_DIR2 = DATA_DIR / "import_issues" / "empty_tsv2"
BREAKING_HIERARCHY_DIR = DATA_DIR / "import_issues" / "breaking_hierarchy"
EMPTY_TSV_IN_UPD_DIR = DATA_DIR / "import_test_upd_empty"
AMBIG_DIR = DATA_DIR / "import de categories ambigues"
VARIOUS_STATES_DIR = DATA_DIR / "import_various_states"

FILE_IMPORT_URL = "/file_import/{project_id}"


def create_project(owner, title, instrument=None):
    with ProjectsService() as sce:
        if instrument:
            prj_id = sce.create(
                owner, CreateProjectReq(title=title, instrument=instrument)
            )
        else:
            prj_id = sce.create(owner, CreateProjectReq(title=title))
        return prj_id


def search_unique_project(asker, title):
    with ProjectsService() as sce:
        srch = sce.search(current_user_id=asker, title_filter=title)
        if len(srch) != 1:
            logging.error(msg="No unique project named '" + title + "'")
        assert len(srch) == 1
        return srch[0]


def dump_project(asker: int, prj_id: int, fd: Any):
    with JsonDumper(asker, prj_id, {}) as sce:
        sce.run(fd)


def do_import(prj_id: int, source_path: str, user_id: int):
    """Import helper for tests"""
    # Do preparation, preparation
    params = ImportReq(source_path=str(source_path))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(user_id)
    job = wait_for_stable(rsp.job_id)
    job = fill_in_if_missing(job)
    check_job_ok(job)
    return prj_id


def fill_in_if_missing(job):
    if job.state == DBJobStateEnum.Asking:
        job_id = job.id
        # Missing user or taxa -> should proceed to step 2 for filling missing
        assert (
            job.progress_msg
            == "Some users or taxonomic references could not be matched"
        )
        # Simulate a missing user and map him to admin
        with JobCRUDService() as sce:
            sce.reply(
                ADMIN_USER_ID,
                job_id,
                {
                    "users": {
                        "admin4test": 1,
                        "elizandro rodriguez": 1,
                        "taxo finder": 1,
                    },
                    "taxa": {},
                },
            )
        return wait_for_stable(job_id)
    else:
        return job


@pytest.mark.parametrize("title", ["Test Create Update"])
def test_import(database, caplog, title, path=str(PLAIN_FILE), instrument=None):
    caplog.set_level(logging.DEBUG)
    # Create a dest project
    prj_id = create_project(ADMIN_USER_ID, title, instrument)
    # Prepare import request
    params = ImportReq(source_path=path)
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    job = fill_in_if_missing(job)
    # assert (job.state, job.progress_pct, job.progress_msg) == (DBJobStateEnum.Finished, 100, "Done")
    # assert job.result["rowcount"] == 8
    return prj_id


# @pytest.mark.skip()
def test_import_again_skipping(database, ccheck, caplog):
    """Re-import similar files into same project
    CANNOT RUN BY ITSELF"""
    caplog.set_level(logging.DEBUG)
    srch = search_unique_project(ADMIN_USER_ID, "Test Create Update")
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = ImportReq(
        source_path=str(PLAIN_FILE), skip_loaded_files=True, skip_existing_objects=True
    )
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    job = fill_in_if_missing(job)
    check_job_errors(job)
    errs = get_job_errors(job)
    found_err = False
    for an_err in errs:
        if "all TSV files were imported before" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
def test_import_again_irrelevant_skipping(database, ccheck, caplog):
    """Re-import similar files into same project
    CANNOT RUN BY ITSELF"""
    caplog.set_level(logging.DEBUG)
    srch = search_unique_project(ADMIN_USER_ID, "Test Create Update")
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = ImportReq(
        source_path=str(EMPTY_TSV_IN_UPD_DIR),
        skip_loaded_files=True,
        skip_existing_objects=True,
    )
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    errs = get_job_errors(job)
    found_err = False
    for an_err in errs:
        if "new TSV file(s) are not compliant" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Test Create Update"])
def test_import_a_bit_more_skipping(database, caplog, title, path=str(PLUS_DIR)):
    """Re-import similar files into same project, with an extra one.
    The extra one has missing values in the TSV.
    CANNOT RUN BY ITSELF"""
    caplog.set_level(logging.DEBUG)
    srch = search_unique_project(ADMIN_USER_ID, title)
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = ImportReq(
        source_path=path, skip_loaded_files=True, skip_existing_objects=True
    )
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    job = fill_in_if_missing(job)
    check_job_ok(job)
    # warns = preparation_out["wrn"]
    # found_imps = 0
    # for a_warn in warns:
    #     if "Analyzing file" in a_warn:
    #         found_imps = True
    # # A single TSV should be analyzed
    # assert found_imps == 1
    # Do real import
    # params = real_params_from_prep_out(task_id, prep_out)
    # params.skip_loaded_files = True
    # params.skip_existing_objects = True
    # # Simulate a missing user and map it to admin
    # params.found_users['elizandro rodriguez'] = {'id': 1}
    # RealImport(prj_id, params).run(ADMIN_USER_ID)
    # TODO: Assert the extra "object_extra" in TSV in data/import_test_plus/m106_mn01_n3_sml


def test_import_again_not_skipping_tsv_skipping_imgs(database, fastapi, ccheck, caplog):
    """Re-import into same project, not skipping TSVs
    CANNOT RUN BY ITSELF"""
    # time.sleep(
    #     0.5
    # )  # TODO: There is a race condition writing invalid rows in obj_header
    caplog.set_level(logging.DEBUG)
    srch = search_unique_project(ADMIN_USER_ID, "Test Create Update")
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    import_plain(fastapi, prj_id)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
        # ecotaxa/ecotaxa_dev#583: Ensure that no extra image was added
        assert "One more image" not in a_msg.getMessage()


def import_plain(fastapi, prj_id):
    params = ImportReq(source_path=str(PLAIN_DIR), skip_existing_objects=True)
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)

    assert job.state == DBJobStateEnum.Asking
    assert job.question == {
        "missing_users": ["admin4test", "elizandro rodriguez"],
        "missing_taxa": ["other", "ozzeur"],
    }

    reply = {
        "users": {"admin4test": 1, "elizandro rodriguez": 1},  # Map to admin
        "taxa": {"other": 99999, "ozzeur": 85011},  # 'other<dead'  # 'other<living'
    }
    # with JobCRUDService() as sce:
    #     sce.reply(ADMIN_USER_ID, rsp.job_id, reply)
    api_reply_to_waiting_job(fastapi, rsp.job_id, reply)
    job = wait_for_stable(rsp.job_id)
    check_job_ok(job)


def import_various(fastapi, prj_id):
    params = ImportReq(source_path=str(VARIOUS_STATES_DIR), skip_existing_objects=True)
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)

    assert job.state == DBJobStateEnum.Asking
    assert job.question == {
        "missing_users": ["elizandro rodriguez"],
        "missing_taxa": [],
    }

    reply = {
        "users": {"elizandro rodriguez": 1},  # Map to admin
        "taxa": {},  # 'other<dead'  # 'other<living'
    }
    # with JobCRUDService() as sce:
    #     sce.reply(ADMIN_USER_ID, rsp.job_id, reply)
    api_reply_to_waiting_job(fastapi, rsp.job_id, reply)
    job = wait_for_stable(rsp.job_id)
    check_job_ok(job)


# @pytest.mark.skip()
def test_import_again_not_skipping_nor_imgs(database, ccheck, caplog):
    """Re-import into same project, not skipping TSVs or images
    CANNOT RUN BY ITSELF"""
    caplog.set_level(logging.DEBUG)
    srch = search_unique_project(ADMIN_USER_ID, "Test Create Update")
    prj_id = srch.projid  # <- need the project from first test
    params = ImportReq(source_path=str(PLAIN_DIR))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    nb_errs = len(
        [an_err for an_err in get_job_errors(job) if "Duplicate object" in an_err]
    )
    assert nb_errs == 11


# @pytest.mark.skip()
def test_equal_dump_prj1(database, ccheck, caplog, tstlogs):
    caplog.set_level(logging.DEBUG)
    out_dump = "prj1.txt"
    with AsciiDumper() as sce:
        sce.run(projid=1, out=tstlogs / out_dump)


# @pytest.mark.skip()
# noinspection DuplicatedCode,PyUnusedLocal
@pytest.mark.parametrize("title", ["Test LS 2"])
def test_import_uvp6(database, caplog, title):
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, title, "UVP6")
    params = ImportReq(source_path=str(V6_FILE))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_ok(job)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    return prj_id


# @pytest.mark.skip()
def test_equal_dump_prj2(database, caplog, tstlogs):
    caplog.set_level(logging.DEBUG)
    out_dump = "prj2.txt"
    with AsciiDumper() as sce:
        sce.run(projid=2, out=tstlogs / out_dump)


# @pytest.mark.skip()
def test_import_empty(database, ccheck, caplog):
    """Nothing relevant to import"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 3")

    params = ImportReq(source_path=str(EMPTY_DIR))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    errors = check_job_errors(job)
    assert len(errors) == 1


# @pytest.mark.skip()
def test_import_empty_tsv(database, ccheck, caplog):
    """a TSV with header but no data"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 3")

    params = ImportReq(source_path=str(EMPTY_TSV_DIR))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    assert len(get_job_errors(job)) == 1


def test_import_empty_tsv2(database, ccheck, caplog):
    """a TSV with nothing at all"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 2.6.3")

    params = ImportReq(source_path=str(EMPTY_TSV_DIR2))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    assert len(get_job_errors(job)) == 1


# @pytest.mark.skip()
def test_import_issues(database, ccheck, caplog):
    """The TSV contains loads of problems"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 4")

    params = ImportReq(source_path=str(ISSUES_DIR))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    errors = get_job_errors(job)
    assert errors == [
        "Invalid Header 'nounderscorecol' in file ecotaxa_m106_mn01_n3_sml.tsv. Format must be Table_Field.",
        "Invalid Header 'unknown_target' in file ecotaxa_m106_mn01_n3_sml.tsv. Unknown table prefix 'unknown'.",
        "Invalid Type '[H]' for Field 'object_wrongtype' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect Type.",
        "Invalid float value 'a' for Field 'object_buggy_float' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Lat. value '100' for Field 'object_lat' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect range -90/+90°.",
        "Invalid Long. value '200' for Field 'object_lon' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect range -180/+180°.",
        "Invalid Date value '20140433' for Field 'object_date' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Time value '9920' for Field 'object_time' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Annotation Status 'predit' for Field 'object_annotation_status' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Date value '2015-11-31' for Field 'object_annotation_date' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Time value '5:31' for Field 'object_annotation_time' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Missing Image 'm106_mn01_n3_sml_1081.jpg2' in file ecotaxa_m106_mn01_n3_sml.tsv. ",
        "Error while reading image 'm106_mn01_n3_sml_corrupted_image.jpg' "
        "from file ecotaxa_m106_mn01_n3_sml.tsv: cannot identify image file '.../m106_mn01_n3_sml_corrupted_image.jpg' <class 'PIL.UnidentifiedImageError'>",
        "Missing object_id in line '6' of file ecotaxa_m106_mn01_n3_sml.tsv. ",
        "Missing Image 'nada.png' in file ecotaxa_m106_mn01_n3_sml.tsv. ",
    ]

    # @pytest.mark.skip()


def test_import_no_valid_category(database, ccheck, caplog):
    """The TSV contains an unknown classification id"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 5")

    params = ImportReq(source_path=str(ISSUES_DIR2))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    errors = get_job_errors(job)
    assert errors == [
        "Some specified classif_id don't exist, correct them prior to reload: 99999999"
    ]


def test_import_no_valid_state_and_others(database, ccheck, caplog, tstlogs):
    """Some states need complementary information that cannot be defaulted"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 10")

    params = ImportReq(source_path=str(ISSUES_DIR5))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    errors = get_job_errors(job)
    assert errors == [
        "When annotation status 'predicted' is provided there has to be a category, in file m106_mn01_n3_sml/ecotaxa_m106_mn01_n3_sml_pls.tsv."
    ]
    check_project(tstlogs, prj_id)


# @pytest.mark.skip()
def test_import_too_many_custom_columns(database, ccheck, caplog):
    """The TSV contains too many custom columns.
    Not a realistic case, but it simulates what happens if importing into a project with
     mappings"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 6")

    params = ImportReq(source_path=str(ISSUES_DIR3))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    errors = get_job_errors(job)
    from DB.Sample import SAMPLE_FREE_COLUMNS
    from DB.Acquisition import ACQUISITION_FREE_COLUMNS
    from DB.Process import PROCESS_FREE_COLUMNS

    compare_errors = []
    for n in range(SAMPLE_FREE_COLUMNS - 2, SAMPLE_FREE_COLUMNS + 1):
        compare_errors.append(
            "Field sample_cus{n}, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too "
            "many custom fields, or bad type.".format(n=str(n))
        )
    for n in range(PROCESS_FREE_COLUMNS - 2, PROCESS_FREE_COLUMNS + 1):
        compare_errors.append(
            "Field process_cus{n}, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too "
            "many custom fields, or bad type.".format(n=str(n))
        )
    for n in range(ACQUISITION_FREE_COLUMNS - 2, ACQUISITION_FREE_COLUMNS + 1):
        compare_errors.append(
            "Field acq_cus{n}, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too "
            "many custom fields, or bad type.".format(n=str(n))
        )

    # assert errors == [
    #    "Field acq_cus29, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too "
    #    "many custom fields, or bad type.",
    #    "Field acq_cus30, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too "
    #    "many custom fields, or bad type.",
    #    "Field acq_cus31, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too "
    #    "many custom fields, or bad type.",
    # ]
    assert errors == compare_errors


def test_import_dups_in_tsv(database, ccheck, caplog):
    """The TSV contains duplicated lines.
    Either without _or without_ 'skip_existing_objects' option, it must not pass preliminary validation,
    as such duplicate is against referential integrity."""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 9")

    expected_errors = [
        "In file m106_mn01_n3_sml/ecotaxa_m106_mn01_n3_sml_pls.tsv, line 4: (Object 'm106_mn01_n3_sml_1120', Image 'm106_mn01_n3_sml_1111.jpg') was seen before."
    ]
    # No skip, should fail
    params = ImportReq(source_path=str(ISSUES_DIR4), skip_existing_objects=False)
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    errors = get_job_errors(job)
    assert errors == expected_errors
    # Skip existing, should fail as well
    params = ImportReq(source_path=str(ISSUES_DIR4), skip_existing_objects=True)
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_errors(job)
    errors = get_job_errors(job)
    assert errors == expected_errors


# @pytest.mark.skip()
def test_import_ambiguous_classification(fastapi, caplog):
    """See https://github.com/oceanomics/ecotaxa_dev/issues/87
    Do it via API"""
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 7")

    url = FILE_IMPORT_URL.format(project_id=prj_id)
    req = {"source_path": str(AMBIG_DIR)}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    api_wait_for_stable_job(fastapi, job_id)
    questions = api_check_job_questions(fastapi, job_id)
    assert questions == {
        "missing_users": [],
        "missing_taxa": ["part (annelida)", "part"],
    }
    api_reply_to_waiting_job(fastapi, job_id, {})
    api_wait_for_stable_job(fastapi, job_id)


# @pytest.mark.skip()
def test_import_uvp6_zip_in_dir(database, caplog):
    """
    An *Images.zip inside a directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 8")

    params = ImportReq(source_path=str(V6_DIR))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    check_job_ok(job)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()


# @pytest.mark.skip()
def test_import_sparse(database, caplog, tstlogs):
    """
    Import a sparse file, some columns are missing.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Sparse")

    params = ImportReq(source_path=str(SPARSE_DIR))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    errors = check_job_errors(job)
    assert errors == [
        "In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field acq_id is mandatory as there are some acq columns: ['acq_hardware', 'acq_imgtype', 'acq_instrument'].",
        "In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field sample_id is mandatory as there are some sample columns: ['sample_program', 'sample_ship', 'sample_stationid'].",
    ]
    print("\n".join(caplog.messages))
    with AsciiDumper() as sce:
        sce.run(projid=prj_id, out=tstlogs / "chk.dmp")


def test_import_broken_TSV(database, caplog, tstlogs):
    """
    Import a TSV with 0 byte.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Sparse")

    params = ImportReq(source_path=str(SPARSE_DIR))
    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    errors = check_job_errors(job)
    assert errors == [
        "In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field acq_id is mandatory as there are some acq columns: ['acq_hardware', 'acq_imgtype', 'acq_instrument'].",
        "In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field sample_id is mandatory as there are some sample columns: ['sample_program', 'sample_ship', 'sample_stationid'].",
    ]
    print("\n".join(caplog.messages))
    with AsciiDumper() as sce:
        sce.run(projid=prj_id, out=tstlogs / "chk.dmp")


# @pytest.mark.skip()
def test_import_breaking_unicity(database, caplog):
    """
    Sample orig_id is unique per project
    Acquisition orig_id is unique per project and belongs to a single Sample
    Process orig_id is unique per acquisition (structurally as it's 1<->1 relationship)
    So, if:
        S("a") -> A("b") -> P ("c")
    Then:
        S("a2") -> A("b") is illegal
    Message should be like 'Acquisition 'b' already belongs to sample 'a' so it cannot be created under 'a2'
    """
    caplog.set_level(logging.DEBUG)
    srch = search_unique_project(ADMIN_USER_ID, "Test Create Update")
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = ImportReq(source_path=str(BREAKING_HIERARCHY_DIR))

    with FileImport(prj_id, params) as sce:
        rsp: ImportRsp = sce.run(ADMIN_USER_ID)
    job = wait_for_stable(rsp.job_id)
    errors = check_job_errors(job)
    assert errors == [
        "Acquisition 'generic_m106_mn01_n1_sml' is already associated with sample "
        "'{'m106_mn01_n1_sml'}', it cannot be associated as well with "
        "'m106_mn01_n1_sml_brk"
    ]


# @pytest.mark.skip()
def test_issue_483(database, ccheck, caplog):
    """
    Too large image.
    """
    # Inject a very small maximum size inside the library, so basically any image
    # will raise a Decompression bomb
    from PIL import Image

    sav = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = 512
    try:
        # This should show as a nice error
        test_import(database, caplog, title="Too large import")
    finally:
        # Restore the lib
        Image.MAX_IMAGE_PIXELS = sav
