# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


import logging
import shutil
from os.path import dirname, realpath
from pathlib import Path

import pytest
# noinspection PyPackageRequirements
from API_models.imports import *
from API_models.crud import *
# Import services
# noinspection PyPackageRequirements
from API_operations.CRUD.Projects import ProjectsService
# noinspection PyPackageRequirements
from API_operations.CRUD.Tasks import TaskService
# noinspection PyPackageRequirements
from API_operations.imports.Import import ImportAnalysis, RealImport
# noinspection PyPackageRequirements
from API_operations.imports.SimpleImport import SimpleImport
from API_operations.AsciiDump import AsciiDumper
from API_operations.Consistency import ProjectConsistencyChecker

# # noinspection PyUnresolvedReferences
# from tests.config_fixture import config
# # noinspection PyUnresolvedReferences
# from tests.db_fixture import database
from starlette import status

from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID, CREATOR_AUTH, CREATOR_USER_ID

DATA_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
PLAIN_FILE = DATA_DIR / "import_test.zip"
V6_FILE = DATA_DIR / "UVP6_example.zip"
V6_DIR = DATA_DIR / "import_uvp6_zip_in_dir"
PLAIN_DIR = DATA_DIR / "import_test"
UPDATE_DIR = DATA_DIR / "import_update"
SPARSE_DIR = DATA_DIR / "import_sparse"
PLUS_DIR = DATA_DIR / "import_test_plus"
ISSUES_DIR = DATA_DIR / "import_issues" / "tsv_issues"
ISSUES_DIR2 = DATA_DIR / "import_issues" / "no_classif_id"
ISSUES_DIR3 = DATA_DIR / "import_issues" / "tsv_too_many_cols"
EMPTY_DIR = DATA_DIR / "import_issues" / "no_relevant_file"
EMPTY_TSV_DIR = DATA_DIR / "import_issues" / "empty_tsv"
BREAKING_HIERARCHY_DIR = DATA_DIR / "import_issues" / "breaking_hierarchy"
EMPTY_TSV_IN_UPD_DIR = DATA_DIR / "import_test_upd_empty"
AMBIG_DIR = DATA_DIR / "import de categories ambigues"


def check_project(prj_id: int):
    problems = ProjectConsistencyChecker(prj_id).run(ADMIN_USER_ID)
    assert problems == []


def real_params_from_prep_out(task_id, prep_out: ImportPrepRsp) -> ImportRealReq:
    return ImportRealReq(task_id=task_id,
                         **prep_out.dict(exclude={'warnings', 'errors'}))


def real_params_from_json_prep_out(task_id, prep_out: Dict) -> Dict:
    ret = {"task_id": task_id}
    ret.update(prep_out)
    for exc in ('warnings', 'errors'):
        if exc in ret:
            del ret[exc]
    return ret


def do_import(prj_id: int, source_path: str, user_id: int):
    """ Import helper for tests """
    # Create a task for this run
    task_id = TaskService().create()
    # Do preparation, preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(source_path))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(user_id)
    # Do real import, reusing prep output
    params = real_params_from_prep_out(task_id, prep_out)
    # Map any not found to admin
    for usr in params.found_users.keys():
        params.found_users[usr] = {'id': 1}
    RealImport(prj_id, params).run(user_id)
    return prj_id


@pytest.mark.parametrize("title", ["Test Create Update"])
def test_import(config, database, caplog, title):
    caplog.set_level(logging.DEBUG)
    # Create a dest project
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title=title))
    # Create a task for this run
    task_id = TaskService().create()
    # user_sce = UserService()
    # Create an admin for mapping
    # Now in SQL
    # user_sce.create("admin", "me@home.fr")
    # Do preparation, preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_FILE))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    # Do real import, reusing prep output
    params = real_params_from_prep_out(task_id, prep_out)
    # Simulate a missing user and map it to admin
    params.found_users['elizandro rodriguez'] = {'id': 1}
    RealImport(prj_id, params).run(ADMIN_USER_ID)
    return prj_id


# @pytest.mark.skip()
def test_import_again_skipping(config, database, caplog):
    """ Re-import similar files into same project
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    srch = ProjectsService().search(current_user_id=ADMIN_USER_ID,
                                    title_filter="Test Create Update")
    assert len(srch) == 1
    prj_id = srch[0].projid  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_FILE),
                           skip_loaded_files=True,
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    errs = prep_out.errors
    found_err = False
    for an_err in errs:
        if "all TSV files were imported before" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
def test_import_again_irrelevant_skipping(config, database, caplog):
    """ Re-import similar files into same project
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    srch = ProjectsService().search(current_user_id=ADMIN_USER_ID,
                                    title_filter="Test Create Update")
    assert len(srch) == 1
    prj_id = srch[0].projid  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(EMPTY_TSV_IN_UPD_DIR),
                           skip_loaded_files=True,
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    errs = prep_out.errors
    found_err = False
    for an_err in errs:
        if "new TSV file(s) are not compliant" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Test Create Update"])
def test_import_a_bit_more_skipping(config, database, caplog, title):
    """ Re-import similar files into same project, with an extra one.
        The extra one has missing values in the TSV.
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    srch = ProjectsService().search(current_user_id=ADMIN_USER_ID,
                                    title_filter=title)
    assert len(srch) == 1
    prj_id = srch[0].projid  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLUS_DIR),
                           skip_loaded_files=True,
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    # warns = preparation_out["wrn"]
    # found_imps = 0
    # for a_warn in warns:
    #     if "Analyzing file" in a_warn:
    #         found_imps = True
    # # A single TSV should be analyzed
    # assert found_imps == 1
    # Do real import
    params = real_params_from_prep_out(task_id, prep_out)
    params.skip_loaded_files = True
    params.skip_existing_objects = True
    # Simulate a missing user and map it to admin
    params.found_users['elizandro rodriguez'] = {'id': 1}
    RealImport(prj_id, params).run(ADMIN_USER_ID)
    # TODO: Assert the extra "object_extra" in TSV in data/import_test_plus/m106_mn01_n3_sml


def test_import_again_not_skipping_tsv_skipping_imgs(config, database, caplog):
    """ Re-import into same project, not skipping TSVs
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    srch = ProjectsService().search(current_user_id=ADMIN_USER_ID,
                                    title_filter="Test Create Update")
    assert len(srch) == 1
    prj_id = srch[0].projid  # <- need the project from first test
    # Do preparation
    import_plain(prj_id, task_id)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
        # ecotaxa/ecotaxa_dev#583: Ensure that no extra image was added
        assert "One more image" not in a_msg.getMessage()


def import_plain(prj_id, task_id):
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_DIR),
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert prep_out.errors == []
    # Do real import
    params = real_params_from_prep_out(task_id, prep_out)
    params.skip_existing_objects = True
    # Simulate a missing user and map it to admin
    params.found_users['elizandro rodriguez'] = {'id': 1}
    # 'other' category is ambiguous as it maps (in test DB) to other<living and other<dead
    params.found_taxa['other'] = 99999  # 'other<dead'
    # 'ozzeur' category is unknown
    params.found_taxa['ozzeur'] = 85011  # 'other<living'
    params.update_mode = True  # TODO, should be in response
    RealImport(prj_id, params).run(ADMIN_USER_ID)


# @pytest.mark.skip()
def test_import_again_not_skipping_nor_imgs(config, database, caplog):
    """ Re-import into same project, not skipping TSVs or images
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    srch = ProjectsService().search(current_user_id=ADMIN_USER_ID,
                                    title_filter="Test Create Update")
    assert len(srch) == 1
    prj_id = srch[0].projid  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_DIR))

    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    nb_errs = len([an_err for an_err in prep_out.errors
                   if "Duplicate object" in an_err])
    assert nb_errs == 11


# @pytest.mark.skip()
def test_equal_dump_prj1(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    out_dump = "prj1.txt"
    sce = AsciiDumper()
    sce.run(projid=1, out=out_dump)


# @pytest.mark.skip()
def test_import_update(config, database, caplog):
    """ Update TSVs """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test Import update"))

    # Plain import first
    import_plain(prj_id, task_id)
    dump_sce = AsciiDumper()
    dump_sce.run(projid=prj_id, out='before_upd.txt')

    # Update using initial import data, should do nothing
    do_import_update(prj_id, caplog, 'Yes', str(PLAIN_DIR))
    print("Import update 0:" + "\n".join(caplog.messages))
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == []

    # Update without classif, 10 cells
    do_import_update(prj_id, caplog, 'Yes')
    print("Import update 1:" + "\n".join(caplog.messages))
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    # 9 fields + 7 derived sun positions
    assert nb_upds == 16
    saves = [msg for msg in caplog.messages if "Batch save objects" in msg]
    assert saves == ["Batch save objects of 0/0/0/0"] * 3

    # Update classif, 2 cells, one classif ID and one classif quality
    do_import_update(prj_id, caplog, 'Cla')
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    print("Import update 2:" + "\n".join(caplog.messages))
    assert nb_upds == 2
    # 1 line corresponds to nothing, on purpose
    nb_notfound = len([msg for msg in caplog.messages if "not found while updating" in msg])
    assert nb_notfound == 2
    dump_sce.run(projid=prj_id, out='after_upd.txt')
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    # ecotaxa/ecotaxa_dev#583: Check that no image was added during the update
    saves = [msg for msg in caplog.messages if "Batch save objects" in msg]
    assert saves == ["Batch save objects of 0/0/0/0"] * 3

    do_import_update(prj_id, caplog, 'Yes')
    print("Import update 3:" + "\n".join(caplog.messages))
    assert len(caplog.messages) > 0
    upds = [msg for msg in caplog.messages if msg.startswith("Updating")]
    assert upds == []
    dump_sce.run(projid=prj_id, out='after_upd_3.txt')

    # Ensure that re-updating updates nothing. This is tricky due to floats storage on DB.


# @pytest.mark.skip()
def do_import_update(prj_id, caplog, classif, source=None):
    task_id = TaskService().create()
    if source is None:
        source = str(UPDATE_DIR)
    params = ImportPrepReq(task_id=task_id,
                           skip_existing_objects=True,
                           update_mode=classif,
                           source_path=source)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert prep_out.errors == []
    params = real_params_from_prep_out(task_id, prep_out)
    params.found_users['elizandro rodriguez'] = {'id': 1}
    params.found_taxa['other'] = 99999  # 'other<dead'
    params.found_taxa['ozzeur'] = 85011  # 'other<living'
    params.skip_existing_objects = True
    params.update_mode = classif
    caplog.clear()
    RealImport(prj_id, params).run(ADMIN_USER_ID)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    # #498: No extra parent should be created
    for a_msg in caplog.records:
        assert "++ ID" not in a_msg.getMessage()


# @pytest.mark.skip()
# noinspection DuplicatedCode
@pytest.mark.parametrize("title", ["Test LS 2"])
def test_import_uvp6(config, database, caplog, title):
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title=title))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(V6_FILE))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    params = real_params_from_prep_out(task_id, prep_out)
    assert len(prep_out.errors) == 0
    # Do real import
    RealImport(prj_id, params).run(ADMIN_USER_ID)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
    return prj_id


# @pytest.mark.skip()
def test_equal_dump_prj2(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    out_dump = "prj2.txt"
    sce = AsciiDumper()
    sce.run(projid=2, out=out_dump)


# @pytest.mark.skip()
def test_import_empty(config, database, caplog):
    """ Nothing relevant to import """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test LS 3"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(EMPTY_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert len(prep_out.errors) == 1


# @pytest.mark.skip()
def test_import_empty_tsv(config, database, caplog):
    """ a TSV but no data """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test LS 3"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(EMPTY_TSV_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert len(prep_out.errors) == 1


# @pytest.mark.skip()
def test_import_issues(config, database, caplog):
    """ The TSV contains loads of problems """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test LS 4"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(ISSUES_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert prep_out.errors == [
        "Invalid Header 'nounderscorecol' in file ecotaxa_m106_mn01_n3_sml.tsv. Format must be Table_Field. Field ignored",
        "Invalid Header 'unknown_target' in file ecotaxa_m106_mn01_n3_sml.tsv. Unknown table prefix. Field ignored",
        "Invalid Type '[H]' for Field 'object_wrongtype' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect Type. Field ignored",
        "Invalid float value 'a' for Field 'object_buggy_float' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Lat. value '100' for Field 'object_lat' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect range -90/+90°.",
        "Invalid Long. value '200' for Field 'object_lon' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect range -180/+180°.",
        "Invalid Date value '20140433' for Field 'object_date' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Time value '9920' for Field 'object_time' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Annotation Status 'predit' for Field 'object_annotation_status' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Missing Image 'm106_mn01_n3_sml_1081.jpg2' in file ecotaxa_m106_mn01_n3_sml.tsv. ",
        "Error while reading Image 'm106_mn01_n3_sml_corrupted_image.jpg' in file ecotaxa_m106_mn01_n3_sml.tsv. <class 'PIL.UnidentifiedImageError'>",
        "Missing object_id in line '5' of file ecotaxa_m106_mn01_n3_sml.tsv. ",
        "Missing Image 'nada.png' in file ecotaxa_m106_mn01_n3_sml.tsv. "]


# @pytest.mark.skip()
def test_import_classif_issue(config, database, caplog):
    """ The TSV contains an unknown classification id """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test LS 5"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(ISSUES_DIR2))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert prep_out.errors == [
        "Some specified classif_id don't exist, correct them prior to reload: 99999999"]


# @pytest.mark.skip()
def test_import_too_many_custom_columns(config, database, caplog):
    """ The TSV contains too many custom columns.
        Not a realistic case, but it simulates what happens if importing into a project with
         mappings """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test LS 6"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(ISSUES_DIR3))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert prep_out.errors == ['Field acq_cus29, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too '
                               'many custom fields, or bad type.',
                               'Field acq_cus30, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too '
                               'many custom fields, or bad type.',
                               'Field acq_cus31, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too '
                               'many custom fields, or bad type.']


IMPORT_PREP_URL = "/import_prep/{project_id}"
IMPORT_REAL_URL = "/import_real/{project_id}"


# @pytest.mark.skip()
def test_import_ambiguous_classification(config, database, fastapi, caplog):
    """ See https://github.com/oceanomics/ecotaxa_dev/issues/87
        Do it via API """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test LS 7"))
    task_id = TaskService().create()

    url = IMPORT_PREP_URL.format(project_id=prj_id)
    req = {"task_id": task_id,
           "source_path": str(AMBIG_DIR)}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    prep_out = rsp.json()
    assert len(prep_out["errors"]) == 0

    url = IMPORT_REAL_URL.format(project_id=prj_id)
    req = real_params_from_json_prep_out(task_id, prep_out)
    with pytest.raises(Exception,
                       match="Column object_annotation_category: no classification of part \(Annelida\) mapped as part \(Annelida\)"):
        # Do real import, this has to fail as we have unmapped taxonomy
        rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)


# @pytest.mark.skip()
def test_import_uvp6_zip_in_dir(config, database, caplog):
    """
        An *Images.zip inside a directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test LS 8"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(V6_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    params = real_params_from_prep_out(task_id, prep_out)
    assert len(prep_out.errors) == 0
    # Do real import
    RealImport(prj_id, params).run(ADMIN_USER_ID)
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()


# @pytest.mark.skip()
def test_import_sparse(config, database, caplog):
    """
        Import a sparse file, some columns are missing.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title="Test Sparse"))
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(SPARSE_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    params = real_params_from_prep_out(task_id, prep_out)
    print(prep_out.errors)
    assert prep_out.errors == \
           [
               "In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field acq_id is mandatory as there are some acq columns: ['acq_hardware', 'acq_imgtype', 'acq_instrument'].",
               "In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field sample_id is mandatory as there are some sample columns: ['sample_program', 'sample_ship', 'sample_stationid']."
           ]
    # Do real import, even if we had problems before.
    RealImport(prj_id, params).run(ADMIN_USER_ID)
    print("\n".join(caplog.messages))
    sce = AsciiDumper()
    sce.run(projid=prj_id, out="chk.dmp")


# @pytest.mark.skip()
def test_import_breaking_unicity(config, database, caplog):
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
    task_id = TaskService().create()
    srch = ProjectsService().search(current_user_id=ADMIN_USER_ID,
                                    title_filter="Test Create Update")
    assert len(srch) == 1
    prj_id = srch[0].projid  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(BREAKING_HIERARCHY_DIR))

    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run(ADMIN_USER_ID)
    assert prep_out.errors == ["Acquisition 'generic_m106_mn01_n1_sml' is already associated with sample "
                               "'{'m106_mn01_n1_sml'}', it cannot be associated as well with "
                               "'m106_mn01_n1_sml_brk"]
    # Do real import, even if we should not...
    params = real_params_from_prep_out(task_id, prep_out)
    # Boom
    with pytest.raises(AssertionError) as e_info:
        RealImport(prj_id, params).run(ADMIN_USER_ID)


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Test Import Images"])
def test_import_images(config, database, caplog, title):
    """
        Simple import with fixed values.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(ADMIN_USER_ID, CreateProjectReq(title=title))

    vals = {"latitude": "abcde",
            "longitude": "456.5",
            "depthmin": "very very low"}
    params = SimpleImportReq(task_id=0,
                             source_path=str(PLAIN_DIR),
                             values=vals)
    rsp = SimpleImport(prj_id, params).run(ADMIN_USER_ID)
    assert rsp.errors == ["'abcde' is not a valid value for SimpleImportFields.latitude",
                          "'456.5' is not a valid value for SimpleImportFields.longitude",
                          "'very very low' is not a valid value for SimpleImportFields.depthmin"]
    # Do real import
    vals["latitude"] = "43.8802"
    vals["longitude"] = "7.2329"
    vals["depthmin"] = "500"
    params.values = vals
    params.task_id = TaskService().create()
    rsp: SimpleImportRsp = SimpleImport(prj_id, params).run(ADMIN_USER_ID)
    print("\n".join(caplog.messages))
    assert rsp.errors == []
    assert rsp.nb_images == 8
    # Check that all went fine
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()

    # Second run, ensure we don't create dummy parents
    caplog.clear()
    rsp: SimpleImportRsp = SimpleImport(prj_id, params).run(ADMIN_USER_ID)
    print("\n2:".join(caplog.messages))
    for a_msg in caplog.records:
        assert a_msg.levelno != logging.ERROR, a_msg.getMessage()
        assert "++ ID" not in a_msg.getMessage()

    return prj_id


IMPORT_IMAGES_URL = "/simple_import/{project_id}"


# @pytest.mark.skip()
@pytest.mark.parametrize("title", ["Simple via fastapi"])
def test_api_import_images(config, database, fastapi, caplog, title):
    """
        Simple import with no fixed values at all, but using the upload directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectsService().create(CREATOR_USER_ID, CreateProjectReq(title=title))
    sce = TaskService()
    task_id = sce.create()
    shutil.copyfile(str(PLAIN_FILE), sce.get_temp(task_id, "uploaded.zip"))

    url = IMPORT_IMAGES_URL.format(project_id=prj_id)
    req = {"task_id": task_id,
           "source_path": "uploaded.zip",
           "values": {}}
    rsp = fastapi.post(url, headers=CREATOR_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    return prj_id


# @pytest.mark.skip()
def test_issue_483(config, database, caplog):
    """
        Too large image.
    """
    # Inject a very small maximum size inside the library
    from PIL import Image
    sav = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = 512
    try:
        test_import(config, database, caplog, title="Too large import")
    finally:
        Image.MAX_IMAGE_PIXELS = sav
