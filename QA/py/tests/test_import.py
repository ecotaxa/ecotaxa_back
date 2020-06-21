# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#


import logging
from os.path import dirname, realpath
from pathlib import Path

import pytest
# noinspection PyPackageRequirements
from api.imports import *
# Import services
# noinspection PyPackageRequirements
from crud.Project import ProjectService
# noinspection PyPackageRequirements
from crud.Task import TaskService
# noinspection PyPackageRequirements
from tasks.Import import ImportAnalysis, RealImport
# noinspection PyPackageRequirements
from tasks.SimpleImport import SimpleImport
from tech.AsciiDump import AsciiDumper

# noinspection PyUnresolvedReferences
from tests.config_fixture import config
# noinspection PyUnresolvedReferences
from tests.db_fixture import database

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
AMBIG_DIR = DATA_DIR / "import de categories ambigues"


def real_params_from_prep_out(task_id, prep_out: ImportPrepRsp) -> ImportRealReq:
    return ImportRealReq(task_id=task_id,
                         **prep_out.dict(exclude={'warnings', 'errors'}))


def test_import(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    # Create a dest project
    prj_id = ProjectService().create("Test LS")
    # Create a task for this run
    task_id = TaskService().create()
    # user_sce = UserService()
    # Create an admin for mapping
    # Now in SQL
    # user_sce.create("admin", "me@home.fr")
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
        if "all TSV files were imported before" in an_err:
            found_err = True
    assert found_err


# @pytest.mark.skip()
def test_import_a_bit_more_skipping(config, database, caplog):
    """ Re-import similar files into same project, with an extra one.
        The extra one has missing values in the TSV.
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
    import_plain(prj_id, task_id)


def import_plain(prj_id, task_id):
    params = ImportPrepReq(task_id=task_id,
                           source_path=str(PLAIN_DIR),
                           skip_existing_objects=True)
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
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


def test_equal_dump_prj1(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    out_dump = "prj1.txt"
    sce = AsciiDumper()
    sce.run(projid=1, out=out_dump)


def test_import_update(config, database, caplog):
    """ Update TSVs """
    caplog.set_level(logging.DEBUG)
    task_id = TaskService().create()
    prj_id = ProjectService().create("Test Import update")
    # Plain import first
    import_plain(prj_id, task_id)
    dump_sce = AsciiDumper()
    dump_sce.run(projid=prj_id, out='before_upd.txt')
    # Update without classif, 10 cells
    do_import_update(prj_id, caplog, 'Yes')
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    print("\n".join(caplog.messages))
    assert nb_upds == 9
    # Update classif, 2 cells, one classif ID and one classif quality
    do_import_update(prj_id, caplog, 'Cla')
    nb_upds = len([msg for msg in caplog.messages if msg.startswith("Updating")])
    print("\n".join(caplog.messages))
    assert nb_upds == 2
    dump_sce.run(projid=prj_id, out='after_upd.txt')


def do_import_update(prj_id, caplog, classif):
    task_id = TaskService().create()
    params = ImportPrepReq(task_id=task_id,
                           skip_existing_objects=True,
                           update_mode=classif,
                           source_path=str(UPDATE_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    assert len(prep_out.errors) == 0
    params = real_params_from_prep_out(task_id, prep_out)
    params.found_users['elizandro rodriguez'] = {'id': 1}
    params.found_taxa['other'] = 99999  # 'other<dead'
    params.found_taxa['ozzeur'] = 85011  # 'other<living'
    params.skip_existing_objects = True
    params.update_mode = classif
    caplog.clear()
    RealImport(prj_id, params).run()


# @pytest.mark.skip()
# noinspection DuplicatedCode
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


def test_equal_dump_prj2(config, database, caplog):
    caplog.set_level(logging.DEBUG)
    out_dump = "prj2.txt"
    sce = AsciiDumper()
    sce.run(projid=2, out=out_dump)


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
    prj_id = ProjectService().create("Test LS 5")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(ISSUES_DIR2))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    assert prep_out.errors == [
        "Some specified classif_id don't exist, correct them prior to reload: 99999999"]


def test_import_too_many_custom_columns(config, database, caplog):
    """ The TSV contains too many custom columns.
        Not a realistic case, but it simulates what happens if importing into a project with
         mappings """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test LS 6")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(ISSUES_DIR3))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    assert prep_out.errors == ['Field acq_cus29, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too '
                               'many custom fields, or bad type.',
                               'Field acq_cus30, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too '
                               'many custom fields, or bad type.',
                               'Field acq_cus31, in file ecotaxa_m106_mn01_n3_sml.tsv, cannot be mapped. Too '
                               'many custom fields, or bad type.']


def test_import_ambiguous_classification(config, database, caplog):
    """ See https://github.com/oceanomics/ecotaxa_dev/issues/87 """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test LS 7")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(AMBIG_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    params = real_params_from_prep_out(task_id, prep_out)
    assert len(prep_out.errors) == 0
    with pytest.raises(Exception):
        # Do real import, this has to fail as we have unmapped taxonomy
        RealImport(prj_id, params).run()


def test_import_uvp6_zip_in_dir(config, database, caplog):
    """
        An *Images.zip inside a directory.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test LS 8")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(V6_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    params = real_params_from_prep_out(task_id, prep_out)
    assert len(prep_out.errors) == 0
    # Do real import
    RealImport(prj_id, params).run()

def test_import_sparse(config, database, caplog):
    """
        Import a sparse file, some columns are missing.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test Sparse")
    task_id = TaskService().create()

    params = ImportPrepReq(task_id=task_id,
                           source_path=str(SPARSE_DIR))
    prep_out: ImportPrepRsp = ImportAnalysis(prj_id, params).run()
    params = real_params_from_prep_out(task_id, prep_out)
    print(prep_out.errors)
    assert prep_out.errors == \
           ["In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field acq_id is mandatory as there are some acq columns: ['acq_hardware', 'acq_imgtype', 'acq_instrument'].",
            "In ecotaxa_20160719B-163000ish-HealyVPR08-2016_d200_h18_roi.tsv, field sample_id is mandatory as there are some sample columns: ['sample_program', 'sample_ship', 'sample_stationid']."
            ]
    # Do real import, even if we had problems before.
    RealImport(prj_id, params).run()
    print("\n".join(caplog.messages))
    sce = AsciiDumper()
    sce.run(projid=prj_id, out="chk.dmp")



def test_import_images(config, database, caplog):
    """
        An all images inside a directory/zip.
    """
    caplog.set_level(logging.DEBUG)
    prj_id = ProjectService().create("Test Import Images")

    vals = {"latitude": "abcde"}
    params = SimpleImportReq(task_id=0,
                             source_path=str(PLAIN_DIR),
                             values=vals)
    rsp = SimpleImport(prj_id, params).run()
    assert rsp.errors == ["'abcde' is not a valid value for latitude"]
    # Do real import
    vals["latitude"] = "43.8802"
    vals["longitude"] = "7.2329"
    params.values = vals
    params.task_id = TaskService().create()
    rsp: SimpleImportRsp = SimpleImport(prj_id, params).run()
    print("\n".join(caplog.messages))
    assert rsp.errors == []
    assert rsp.nb_images == 8
