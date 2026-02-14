# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
from os.path import dirname, realpath
from pathlib import Path

import pytest
from starlette import status

from API_models.crud import *

# noinspection PyPackageRequirements
from API_operations.AsciiDump import AsciiDumper

# Import services
# noinspection PyPackageRequirements
from API_operations.CRUD.Projects import ProjectsService
from API_operations.JsonDumper import JsonDumper

# noinspection PyPackageRequirements
from DB.Job import DBJobStateEnum
from tests.api_wrappers import (
    api_file_import,
    api_wait_for_stable_job,
    api_check_job_questions,
    UPLOAD_FILE_URL,
    REMOVE_FILE_URL,
)
from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID, CREATOR_USER_ID, CREATOR_AUTH
from tests.jobs import (
    check_job_ok,
    check_job_errors,
    api_reply_to_waiting_job,
)
from tests.logspy_feature import DBWRITER_LOG
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
PLUS_MORE_DIR = DATA_DIR / "import_test_plus_more"
JUST_PREDICTED_DIR = DATA_DIR / "import_just_predicted"
V_OR_D_ONLY_DIR = DATA_DIR / "import_v_or_d_just_state"
WEIRD_DIR = DATA_DIR / "import_test_weird"
ISSUES_DIR = DATA_DIR / "import_issues" / "tsv_issues"
ISSUES_DIR2 = DATA_DIR / "import_issues" / "no_classif_id"
ISSUES_DIR3 = DATA_DIR / "import_issues" / "tsv_too_many_cols"
ISSUES_DIR4 = DATA_DIR / "import_issues" / "duplicate_in_tsv"
ISSUES_DIR5 = DATA_DIR / "import_issues" / "predicted_but_what"
ISSUES_DIR6 = DATA_DIR / "import_issues" / "classif_without_state"
ISSUES_DIR7 = DATA_DIR / "import_issues" / "extra_data_without_header"
MIX_OF_STATES = DATA_DIR / "import_mixed_states"
EMPTY_DIR = DATA_DIR / "import_issues" / "no_relevant_file"
EMPTY_TSV_DIR = DATA_DIR / "import_issues" / "empty_tsv"
EMPTY_TSV_DIR2 = DATA_DIR / "import_issues" / "empty_tsv2"
BREAKING_HIERARCHY_DIR = DATA_DIR / "import_issues" / "breaking_hierarchy"
EMPTY_TSV_IN_UPD_DIR = DATA_DIR / "import_test_upd_empty"
AMBIG_DIR = DATA_DIR / "import de categories ambigues"
VARIOUS_STATES_DIR = DATA_DIR / "import_various_states"
IMPORT_TOT_VOL = DATA_DIR / "import_test_tot_vol"
IMPORT_TOT_VOL_UPDATE = DATA_DIR / "import_test_tot_vol_update"
IMPORT_TOT_VOL_BAD_UPDATE = DATA_DIR / "import_test_tot_vol_bad_update"


def create_project(owner, title, instrument=None, access="1"):
    with ProjectsService() as sce:
        if instrument:
            prj_id = sce.create(
                owner,
                CreateProjectReq(title=title, instrument=instrument, access=access),
            )
        else:
            prj_id = sce.create(owner, CreateProjectReq(title=title, access=access))
        return prj_id


def search_unique_project(asker, title):
    with ProjectsService() as sce:
        srch = sce.search(current_user_id=asker, title_filter=title)
        if len(srch) != 1:
            logging.error(msg="No unique project named '" + title + "'")
        assert len(srch) == 1, f"Projects with title '{title}':" + str(
            [a_prj.projid for a_prj in srch]
        )
        return srch[0]


def dump_project(asker: int, prj_id: int, fd: Any):
    with JsonDumper(asker, prj_id, {}) as sce:
        sce.run(fd)


def do_import(fastapi, prj_id: int, source_path: str, auth: dict):
    """Import helper for tests"""
    params = dict(source_path=str(source_path))
    rsp = api_file_import(fastapi, prj_id, params, auth)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    job = fill_in_if_missing(fastapi, job)
    check_job_ok(job)
    return prj_id


def fill_in_if_missing(fastapi, job):
    if job.state == DBJobStateEnum.Asking:
        job_id = job.id
        # Missing user or taxa -> should proceed to step 2 for filling missing
        assert (
            job.progress_msg
            == "Some users or taxonomic references could not be matched"
        )
        # Simulate a missing user and map him to admin
        reply = {
            "users": {
                "admin4test": 1,
                "elizandro rodriguez": 1,
                "taxo finder": 1,
            },
            "taxa": {},
        }
        api_reply_to_waiting_job(fastapi, job_id, reply)
        return api_wait_for_stable_job(fastapi, job_id)
    else:
        return job


ONE_WITH_TITLE = "Test Create Update"


@pytest.mark.parametrize("title", [ONE_WITH_TITLE])
def test_import(fastapi, title, path=str(PLAIN_FILE), instrument=None):
    do_test_import(fastapi, title, path, instrument)


def do_test_import(fastapi, title, path=str(PLAIN_FILE), instrument=None):
    # Create a dest project
    prj_id = create_project(ADMIN_USER_ID, title, instrument)
    # Ensure a single one
    if title == ONE_WITH_TITLE:
        search_unique_project(
            ADMIN_USER_ID, title
        )  # If this fails it means you imported the test in another module so it was executed twice
    # Prepare import request
    params = dict(source_path=path)
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    job = fill_in_if_missing(fastapi, job)
    assert (job.state, job.progress_pct, job.progress_msg) == (
        DBJobStateEnum.Finished,
        100,
        "Done",
    ), job
    # assert job.result["rowcount"] == 8
    return prj_id


# @pytest.mark.skip()
def test_import_again_skipping(fastapi, ccheck):
    """Re-import similar files into same project
    CANNOT RUN BY ITSELF"""
    srch = search_unique_project(ADMIN_USER_ID, ONE_WITH_TITLE)
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = dict(
        source_path=str(PLAIN_FILE), skip_loaded_files=True, skip_existing_objects=True
    )
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    job = fill_in_if_missing(fastapi, job)
    errs = check_job_errors(job)
    found_err = False
    for an_err in errs:
        if "all TSV files were imported before" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
def test_import_again_irrelevant_skipping(fastapi, ccheck):
    """Re-import similar files into same project
    CANNOT RUN BY ITSELF"""
    srch = search_unique_project(ADMIN_USER_ID, ONE_WITH_TITLE)
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = dict(
        source_path=str(EMPTY_TSV_IN_UPD_DIR),
        skip_loaded_files=True,
        skip_existing_objects=True,
    )
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errs = check_job_errors(job)
    found_err = False
    for an_err in errs:
        if "new TSV file(s) are not compliant" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
@pytest.mark.parametrize("title", [ONE_WITH_TITLE])
def test_import_a_bit_more_skipping(fastapi, title, path=str(PLUS_DIR)):
    """Re-import similar files into same project, with an extra one.
    The extra one has missing values in the TSV.
    CANNOT RUN BY ITSELF"""
    do_import_a_bit_more_skipping(fastapi, title, path)


def do_import_a_bit_more_skipping(fastapi, title, path=str(PLUS_DIR)):
    srch = search_unique_project(ADMIN_USER_ID, title)
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = dict(source_path=path, skip_loaded_files=True, skip_existing_objects=True)
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    job = fill_in_if_missing(fastapi, job)
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


def test_import_again_not_skipping_tsv_skipping_imgs(fastapi, ccheck, caplog):
    """Re-import into same project, not skipping TSVs
    CANNOT RUN BY ITSELF"""
    # time.sleep(
    #     0.5
    # )  # TODO: There is a race condition writing invalid rows in obj_header
    caplog.set_level(logging.DEBUG)
    srch = search_unique_project(ADMIN_USER_ID, ONE_WITH_TITLE)
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    import_plain(fastapi, prj_id)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
        # ecotaxa/ecotaxa_dev#583: Ensure that no extra image was added
        assert "One more image" not in a_msg.getMessage()


def import_plain(fastapi, prj_id):
    params = dict(source_path=str(PLAIN_DIR), skip_existing_objects=True)
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])

    assert job.state == DBJobStateEnum.Asking
    assert job.question == {
        "missing_users": ["admin4test", "elizandro rodriguez"],
        "missing_taxa": ["other", "ozzeur"],
    }

    reply = {
        "users": {"admin4test": 1, "elizandro rodriguez": 1},  # Map to admin
        "taxa": {"other": 99999, "ozzeur": 85011},  # 'other<dead'  # 'other<living'
    }
    api_reply_to_waiting_job(fastapi, rsp.json()["job_id"], reply)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    check_job_ok(job)


def import_various(fastapi, prj_id):
    params = dict(source_path=str(VARIOUS_STATES_DIR), skip_existing_objects=True)
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])

    assert job.state == DBJobStateEnum.Asking
    assert job.question == {
        "missing_users": ["elizandro rodriguez"],
        "missing_taxa": [],
    }

    reply = {
        "users": {"elizandro rodriguez": 1},  # Map to admin
        "taxa": {},  # 'other<dead'  # 'other<living'
    }
    api_reply_to_waiting_job(fastapi, rsp.json()["job_id"], reply)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    check_job_ok(job)


# @pytest.mark.skip()
def test_import_again_not_skipping_nor_imgs(fastapi, ccheck):
    """Re-import into same project, not skipping TSVs or images
    CANNOT RUN BY ITSELF"""
    srch = search_unique_project(ADMIN_USER_ID, ONE_WITH_TITLE)
    prj_id = srch.projid  # <- need the project from first test
    params = dict(source_path=str(PLAIN_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    nb_errs = len([an_err for an_err in errors if "already in EcoTaxa" in an_err])
    assert nb_errs == 11


# @pytest.mark.skip()
def test_equal_dump_prj1(fastapi, ccheck, tstlogs):
    out_dump = "prj1.txt"
    with AsciiDumper() as sce:
        sce.run(projid=1, out=tstlogs / out_dump)


# @pytest.mark.skip()
# noinspection DuplicatedCode,PyUnusedLocal
@pytest.mark.parametrize("title", ["Test LS 2"])
def test_import_uvp6(fastapi, caplog, title):
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.INFO, DBWRITER_LOG)
    do_import_uvp6(fastapi, title)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()


def do_import_uvp6(fastapi, title):
    prj_id = create_project(ADMIN_USER_ID, title, "UVP6", "2")
    params = {"source_path": str(V6_FILE)}
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    check_job_ok(job)
    return prj_id


# @pytest.mark.skip()
def test_equal_dump_prj2(fastapi, tstlogs):
    out_dump = "prj2.txt"
    with AsciiDumper() as sce:
        sce.run(projid=2, out=tstlogs / out_dump)


# @pytest.mark.skip()
def test_import_empty(fastapi, ccheck):
    """Nothing relevant to import"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 3")

    params = dict(source_path=str(EMPTY_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert len(errors) == 1


# @pytest.mark.skip()
def test_import_empty_tsv(fastapi, ccheck):
    """a TSV with header but no data"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 3")

    params = dict(source_path=str(EMPTY_TSV_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert len(errors) == 1


def test_import_empty_tsv2(fastapi, ccheck):
    """a TSV with nothing at all"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 2.6.3")

    params = dict(source_path=str(EMPTY_TSV_DIR2))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert len(errors) == 1


# @pytest.mark.skip()
def test_import_issues(fastapi, ccheck):
    """The TSV contains loads of problems"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 4")

    params = dict(source_path=str(ISSUES_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "In [base]/ecotaxa_m106_mn01_n3_sml.tsv:",
        " - Invalid Header 'nounderscorecol'. Format must be Table_Field.",
        " - Invalid Header 'unknown_target'. Unknown table prefix 'unknown'.",
        " - Invalid Type '[H]' for field 'object_wrongtype'.",
        " - line 3: Invalid float value 'a' for field 'object_buggy_float'.",
        " - line 3: Invalid Lat. value '100' for field 'object_lat'. Correct range is -90/+90°.",
        " - line 3: Invalid Long. value '200' for field 'object_lon'. Correct range is -180/+180°.",
        " - line 3: Invalid Date value '20140433' for field 'object_date'.",
        " - line 3: Invalid Time value '9920' for field 'object_time'.",
        " - line 3: Invalid Annotation Status 'predit' for field 'object_annotation_status'.",
        " - line 5: Invalid Date value '2015-11-31' for field 'object_annotation_date'.",
        " - line 5: Invalid Time value '5:31' for field 'object_annotation_time'.",
        " - line 6: Missing Image 'm106_mn01_n3_sml_1081.jpg2'.",
        " - line 7: Error while reading image 'm106_mn01_n3_sml_corrupted_image.jpg': cannot identify image file '.../m106_mn01_n3_sml_corrupted_image.jpg' <class 'PIL.UnidentifiedImageError'>",
        " - line 8: Missing object_id.",
        " - line 8: Missing Image 'nada.png'.",
    ]


def test_import_no_valid_category(fastapi, ccheck):
    """The TSV contains an unknown classification id"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 5")

    params = dict(source_path=str(ISSUES_DIR2))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "Some specified classif_id don't exist, correct them prior to reload: 99999999"
    ]


def test_import_no_valid_state_and_others(fastapi, ccheck, tstlogs):
    """Some states need complementary information that cannot be defaulted"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 10")

    params = dict(source_path=str(ISSUES_DIR5))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "In [base]/m106_mn01_n3_sml/ecotaxa_m106_mn01_n3_sml_pls.tsv:",
        " - line 3: When annotation status 'predicted' is provided there has to be a category.",
    ]
    check_project(tstlogs, prj_id)


def test_import_classif_without_state(fastapi, ccheck, tstlogs):
    """Importing a classification implies having a state"""
    prj_id = create_project(ADMIN_USER_ID, "Test import problem 11")

    params = dict(source_path=str(ISSUES_DIR6))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "In [base]/m106_mn01_n3_sml/ecotaxa_m106_mn01_n3_sml_pls.tsv:",
        " - line 3: When a category (84963) is provided it has to be with a status.",
    ]
    check_project(tstlogs, prj_id)


def test_import_data_without_header(fastapi, ccheck, tstlogs):
    """Mistake, no header but some data in a column"""
    prj_id = create_project(ADMIN_USER_ID, "Test import problem 12")

    params = dict(source_path=str(ISSUES_DIR7))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "In [base]/ecotaxa_m106_mn04_n1_sml.tsv:",
        " - line 3: Value(s) ['Extra', 'Extra2'] must not be in a header-less column.",
    ]
    check_project(tstlogs, prj_id)


def test_import_state_without_related(fastapi, ccheck, tstlogs):
    """Importing just 'V' or 'D' is OK, we provide reasonable defaults"""
    prj_id = create_project(ADMIN_USER_ID, "Test import case 12")

    params = dict(source_path=str(V_OR_D_ONLY_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    check_job_ok(job)
    check_project(tstlogs, prj_id)


# @pytest.mark.skip()
def test_import_too_many_custom_columns(fastapi, ccheck):
    """The TSV contains too many custom columns.
    Not a realistic case, but it simulates what happens if importing into a project with
     mappings"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 6")

    params = dict(source_path=str(ISSUES_DIR3))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    from DB.Sample import SAMPLE_FREE_COLUMNS
    from DB.Acquisition import ACQUISITION_FREE_COLUMNS
    from DB.Process import PROCESS_FREE_COLUMNS

    compare_errors = ["In [base]/ecotaxa_m106_mn01_n3_sml.tsv:"]
    for n in range(SAMPLE_FREE_COLUMNS - 2, SAMPLE_FREE_COLUMNS + 1):
        compare_errors.append(
            " - Field sample_cus{n} cannot be mapped. Too "
            "many custom fields, or bad type.".format(n=str(n))
        )
    for n in range(PROCESS_FREE_COLUMNS - 2, PROCESS_FREE_COLUMNS + 1):
        compare_errors.append(
            " - Field process_cus{n} cannot be mapped. Too "
            "many custom fields, or bad type.".format(n=str(n))
        )
    for n in range(ACQUISITION_FREE_COLUMNS - 2, ACQUISITION_FREE_COLUMNS + 1):
        compare_errors.append(
            " - Field acq_cus{n} cannot be mapped. Too "
            "many custom fields, or bad type.".format(n=str(n))
        )

    assert errors == compare_errors


def test_import_dups_in_tsv(fastapi, ccheck):
    """The TSV contains duplicated lines.
    Either without _or without_ 'skip_existing_objects' option, it must not pass preliminary validation,
    as such duplicate is against referential integrity."""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 9")

    expected_errors = [
        "In [base]/m106_mn01_n3_sml/ecotaxa_m106_mn01_n3_sml_pls.tsv:",
        " - line 4: (Object 'm106_mn01_n3_sml_1120', Image 'm106_mn01_n3_sml_1111.jpg') is already in this TSV line 3.",
    ]
    # No skip, should fail
    params = dict(source_path=str(ISSUES_DIR4), skip_existing_objects=False)
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == expected_errors
    # Skip existing, should fail as well
    params = dict(source_path=str(ISSUES_DIR4), skip_existing_objects=True)
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == expected_errors


# @pytest.mark.skip()
def test_import_ambiguous_classification(fastapi):
    """See https://github.com/oceanomics/ecotaxa_dev/issues/87
    Do it via API"""
    prj_id = create_project(ADMIN_USER_ID, "Test LS 7")

    req = {"source_path": str(AMBIG_DIR)}
    rsp = api_file_import(fastapi, prj_id, req, ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    api_wait_for_stable_job(fastapi, job_id)
    questions = api_check_job_questions(fastapi, job_id)
    assert questions == {
        "missing_users": [],
        "missing_taxa": ["part (annelida)", "part"],
    }
    api_reply_to_waiting_job(
        fastapi, job_id, {"users": {}, "taxa": {"part (annelida)": 1, "part": 2}}
    )
    job = api_wait_for_stable_job(fastapi, job_id)
    check_job_ok(job)


# @pytest.mark.skip()
def test_import_uvp6_zip_in_dir(fastapi, caplog):
    """
    An *Images.zip inside a directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test LS 8")

    params = dict(source_path=str(V6_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    check_job_ok(job)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()


# @pytest.mark.skip()
def test_import_sparse(fastapi, caplog, tstlogs):
    """
    Import a sparse file, some columns are missing.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Sparse")

    params = dict(source_path=str(SPARSE_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "In [base]/ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv:",
        " - Field acq_id is mandatory as there are some acq columns: ['acq_hardware', 'acq_imgtype', 'acq_instrument'].",
        " - Field sample_id is mandatory as there are some sample columns: ['sample_program', 'sample_ship', 'sample_stationid'].",
    ]
    with AsciiDumper() as sce:
        sce.run(projid=prj_id, out=tstlogs / "chk.dmp")


def test_import_broken_TSV(fastapi, caplog, tstlogs):
    """
    Import a TSV with 0 byte.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = create_project(ADMIN_USER_ID, "Test Sparse")

    params = dict(source_path=str(SPARSE_DIR))
    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "In [base]/ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv:",
        " - Field acq_id is mandatory as there are some acq columns: ['acq_hardware', 'acq_imgtype', 'acq_instrument'].",
        " - Field sample_id is mandatory as there are some sample columns: ['sample_program', 'sample_ship', 'sample_stationid'].",
    ]
    with AsciiDumper() as sce:
        sce.run(projid=prj_id, out=tstlogs / "chk.dmp")


# @pytest.mark.skip()
def test_import_breaking_unicity(fastapi):
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
    srch = search_unique_project(ADMIN_USER_ID, ONE_WITH_TITLE)
    prj_id = srch.projid  # <- need the project from first test
    # Do preparation
    params = dict(source_path=str(BREAKING_HIERARCHY_DIR))

    rsp = api_file_import(fastapi, prj_id, params, ADMIN_AUTH)
    job = api_wait_for_stable_job(fastapi, rsp.json()["job_id"])
    errors = check_job_errors(job)
    assert errors == [
        "Acquisition 'generic_m106_mn01_n1_sml' is already associated with sample "
        "'{'m106_mn01_n1_sml'}', it cannot be associated as well with "
        "'m106_mn01_n1_sml_brk"
    ]


def test_uvp6_via_myfile(fastapi, caplog):
    prj_id = create_project(CREATOR_USER_ID, "UVP6 via MyFiles")
    local_file = SHARED_DIR / V6_FILE
    with open(local_file, "rb") as fin:
        upload_rsp = fastapi.post(
            UPLOAD_FILE_URL,
            headers=CREATOR_AUTH,
            files={"file": fin},
        )
        assert upload_rsp.status_code == 200
    no_zip = local_file.name.replace(".zip", "")

    list_rsp = fastapi.get(f"{UPLOAD_FILE_URL}", headers=CREATOR_AUTH)
    assert list_rsp.status_code == 200
    user_files = list_rsp.json()
    assert no_zip in [a_file["name"] for a_file in user_files["entries"]]

    do_import(fastapi, prj_id, no_zip, CREATOR_AUTH)
    # Check that objects were imported
    rsp = fastapi.post(
        f"/object_set/{prj_id}/summary",
        headers=CREATOR_AUTH,
        params={"only_total": False},
        json={},
    )
    assert rsp.json()["total_objects"] == 15

    assert f"Importing UVP6 file [base]/b_da_19_Images" in caplog.messages
