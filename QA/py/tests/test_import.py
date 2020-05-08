# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


import logging
from os.path import dirname, realpath
from pathlib import Path

# noinspection PyPackageRequirements
# noinspection PyPackageRequirements
from api.imports import *
# Import services
# noinspection PyPackageRequirements
from crud.Project import ProjectService
# noinspection PyPackageRequirements
from crud.Task import TaskService
# noinspection PyPackageRequirements
from crud.User import UserService
# noinspection PyPackageRequirements
from tasks.Import import ImportAnalysis, RealImport

# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database

DATA_DIR = (Path(dirname(realpath(__file__))) / ".." / "data").resolve()
V6_FILE = DATA_DIR / "UVP6_example.zip"
PLAIN_FILE = DATA_DIR / "import_test.zip"
PLAIN_DIR = DATA_DIR / "import_test"
PLUS_DIR = DATA_DIR / "import_test_plus"
ISSUES_DIR = DATA_DIR / "import_issues" / "tsv_issues"
ISSUES_DIR2 = DATA_DIR / "import_issues" / "no_classif_id"
EMPTY_DIR = DATA_DIR / "import_issues" / "no_relevant_file"


def real_params_from_prep_out(task_id, prep_out: ImportPrepRsp) -> ImportRealReq:
    return ImportRealReq(task_id=task_id,
                         **prep_out.dict(exclude={'warnings', 'errors'}))


def test_import(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    # Create a dest project
    prj_id = ProjectService().create("Test LS")
    # Create a task for this run
    task_id = TaskService().create()
    user_sce = UserService()
    # Create an admin for mapping
    user_sce.create("admin", "me@home.fr")
    # Do preparation, preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_FILE))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    # Do real import, real, reusing prep output
    params = real_params_from_prep_out(task_id, prep_out)
    # Simulate a missing user and map it to admin
    params.found_users['elizandro rodriguez'] = {'id': 1}
    print(params)
    RealImport(prj_id, params).run()

    # out_dump = "new.txt"
    # sce = AsciiDumper()
    # print("All is in projet #%d, doing dump into %s" % (params["prj"], out_dump))
    # sce.run(projid=params["prj"], out=out_dump)


# @pytest.mark.skip()
def test_import_again_skipping(config, database, caplog):
    """ Re-import similar files into same project
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    prj_id = 1  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_FILE),
                           skip_loaded_files=True,
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    errs = prep_out.errors
    found_err = False
    for an_err in errs:
        if "No object to import" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
def test_import_a_bit_more_skipping(config, database, caplog):
    """ Re-import similar files into same project, with an extra one
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    prj_id = 1  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLUS_DIR),
                           skip_loaded_files=True,
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
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
    RealImport(prj_id, params).run()
    # TODO: Assert the extra "object_extra" in TSV in data/import_test_plus/m106_mn01_n3_sml


# @pytest.mark.skip()
def test_import_again_not_skipping_tsv_skipping_imgs(config, database, caplog):
    """ Re-import into same project, not skipping TSVs
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    prj_id = 1  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_DIR),
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    # Do real import
    params = real_params_from_prep_out(task_id, prep_out)
    params.skip_existing_objects = True
    # Simulate a missing user and map it to admin
    params.found_users['elizandro rodriguez'] = {'id': 1}
    RealImport(prj_id, params).run()


# @pytest.mark.skip()
def test_import_again_not_skipping_nor_imgs(config, database, caplog):
    """ Re-import into same project, not skipping TSVs or images
        CANNOT RUN BY ITSELF """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    prj_id = 1  # <- need the project from first test
    # Do preparation
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_DIR))

    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    nb_errs = len([an_err for an_err in prep_out.errors
                   if "Duplicate object" in an_err])
    assert nb_errs == 11


# @pytest.mark.skip()
def test_import_uvp6(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test LS 2")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(V6_FILE))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    params = real_params_from_prep_out(task_id, prep_out)
    assert len(prep_out.errors) == 0
    # Do real import
    RealImport(prj_id, params).run()


# @pytest.mark.skip()
def test_import_empty(config, database, caplog):
    """ Nothing relevant to import """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test LS 3")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(EMPTY_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    assert len(prep_out.errors) == 1


# @pytest.mark.skip()
def test_import_issues(config, database, caplog):
    """ The TSV contains loads of problems """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test LS 4")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(ISSUES_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    assert prep_out.errors == [
        "Invalid Header 'nounderscorecol' in file ecotaxa_m106_mn01_n3_sml.tsv. Format must be Table_Field. Field ignored",
        "Invalid Header 'unknown_target' in file ecotaxa_m106_mn01_n3_sml.tsv. Unknown table prefix. Field ignored",
        "Invalid Type '[H]' for Field 'object_wrongtype' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect Type. Field ignored",
        "Invalid float value 'a' for Field 'object_buggy_float' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Lat. value '100' for Field 'object_lat' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect range -90/+90°.",
        "Invalid Long. value '200' for Field 'object_lon' in file ecotaxa_m106_mn01_n3_sml.tsv. Incorrect range -180/+180°.",
        "Invalid Date value '20140433' for Field 'object_date' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Time value '009920' for Field 'object_time' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Invalid Annotation Status 'predit' for Field 'object_annotation_status' in file ecotaxa_m106_mn01_n3_sml.tsv.",
        "Missing Image 'm106_mn01_n3_sml_1081.jpg2' in file ecotaxa_m106_mn01_n3_sml.tsv. ",
        "Error while reading Image 'm106_mn01_n3_sml_corrupted_image.jpg' in file ecotaxa_m106_mn01_n3_sml.tsv. <class 'PIL.UnidentifiedImageError'>",
        "Missing object_id in line '5' of file ecotaxa_m106_mn01_n3_sml.tsv. ",
        "Missing Image 'nada.png' in file ecotaxa_m106_mn01_n3_sml.tsv. "]


# @pytest.mark.skip()
def test_import_classif_issue(config, database, caplog):
    """ The TSV contains an unknown classification id """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test LS 5")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(ISSUES_DIR2))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    assert prep_out.errors == ["Some specified classif_id don't exist, correct them prior to reload: 99999999"]
