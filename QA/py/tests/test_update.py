# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import logging

from API_models.crud import *
# Import services
from API_operations.CRUD.ObjectParents import SamplesService, AcquisitionsService, ProcessesService
from API_operations.JsonDumper import JsonDumper
from API_operations.ObjectManager import ObjectManager
from deepdiff import DeepDiff

from tests.test_import import ADMIN_USER_ID, test_import_uvp6
from tests.test_subset_merge import check_project

OUT_JSON_REF = "out_upd_tst.json"
OUT_JSON_MODIF = "out_upd_tst_after.json"


def upd(col, val) -> ColUpdate:
    ret = {"ucol": col,
           "uval": val}
    return ret


def test_updates(config, database, caplog):
    caplog.set_level(logging.ERROR)
    prj_id = test_import_uvp6(config, database, caplog, "Test Subset Merge")
    check_project(prj_id)

    # Dump the project before changes
    with open(OUT_JSON_REF, "w") as fd:
        JsonDumper(ADMIN_USER_ID, prj_id, {}).run(fd)
    with open(OUT_JSON_REF) as fd:
        json_prj = json.load(fd)
    sample_id = json_prj["samples"][0]["id"]
    acquis_id = json_prj["samples"][0]["acquisitions"][0]["id"]
    process_id = json_prj["samples"][0]["acquisitions"][0]["processings"][0]["id"]

    # Typo in column name
    nb_upd = SamplesService().update_set(ADMIN_USER_ID, [sample_id], ColUpdateList([upd("chip", "sagitta4")]))
    assert nb_upd == 0

    # Update ship in the only sample, and a date to see
    upds = ColUpdateList([upd("ship", "sagitta4"),
                          upd("sampledatetime", "20200208-111218")])
    nb_upd = SamplesService().update_set(ADMIN_USER_ID, [sample_id, sample_id], upds)
    assert nb_upd == 1

    # Update 1st acquisition, and a float, to see
    upds = ColUpdateList([upd("orig_id", "aid5"),
                          upd("exp", "0.6")])
    nb_upd = AcquisitionsService().update_set(ADMIN_USER_ID, [acquis_id], upds)
    assert nb_upd == 1

    # Update 1st process
    upds = ColUpdateList([upd("date", "20200325"),
                          upd("invert", "n")])
    nb_upd = ProcessesService().update_set(ADMIN_USER_ID, [process_id], upds)
    assert nb_upd == 1

    # Update all objects
    objs = ObjectManager().query(ADMIN_USER_ID, prj_id, {})
    objs = [an_obj[0] for an_obj in objs]
    assert len(objs) == 15
    # Wrong column
    nb_upd = ObjectManager().update_set(ADMIN_USER_ID, objs, ColUpdateList([upd("chip", "sagitta4")]))
    assert nb_upd == 0
    # Free column
    nb_upd = ObjectManager().update_set(ADMIN_USER_ID, objs, ColUpdateList([upd("area", "10")]))
    assert nb_upd == 15
    # Plain column
    nb_upd = ObjectManager().update_set(ADMIN_USER_ID, objs, ColUpdateList([upd("depth_min", "10")]))
    assert nb_upd == 15

    # Dump the project after changes
    with open(OUT_JSON_MODIF, "w") as fd:
        JsonDumper(ADMIN_USER_ID, prj_id, {}).run(fd)

    # Special column
    # TODO: Avoiding diff on purpose, it's just to cover code.
    nb_upd = ObjectManager().update_set(ADMIN_USER_ID, objs, ColUpdateList([upd("classif_id", "100")]))
    assert nb_upd == 15

    # Json diff
    with open(OUT_JSON_REF) as fd1:
        json_src = json.load(fd1)
    with open(OUT_JSON_MODIF) as fd2:
        json_subset = json.load(fd2)
    diffs = DeepDiff(json_src, json_subset)

    # Validate by removing all know differences b/w source and subset
    assert 'iterable_item_added' not in diffs
    assert 'iterable_item_removed' not in diffs
    assert 'dictionary_item_added' not in diffs
    assert 'dictionary_item_removed' not in diffs
    changed_values = diffs['values_changed']
    assert changed_values == {
        "root['samples'][0]['acquisitions'][0]['aid']": {'new_value': 'aid5',
                                                         'old_value': 'b_da_19'},
        "root['samples'][0]['acquisitions'][0]['exp']": {'new_value': '0.6',
                                                         'old_value': '1.257'},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['date']": {'new_value': '20200325',
                                                                            'old_value': '20200317'},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['invert']": {'new_value': 'n',
                                                                              'old_value': 'y'},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][0]['area']": {'new_value': 10.0,
                                                                                          'old_value': 207.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][0]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 194.63},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][10]['area']": {'new_value': 10.0,
                                                                                           'old_value': 119.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][10]['depth_min']": {'new_value': 10.0,
                                                                                                'old_value': 215.76},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][11]['area']": {'new_value': 10.0,
                                                                                           'old_value': 137.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][11]['depth_min']": {'new_value': 10.0,
                                                                                                'old_value': 224.44},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][12]['area']": {'new_value': 10.0,
                                                                                           'old_value': 93.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][12]['depth_min']": {'new_value': 10.0,
                                                                                                'old_value': 252.235},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][13]['area']": {'new_value': 10.0,
                                                                                           'old_value': 165.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][13]['depth_min']": {'new_value': 10.0,
                                                                                                'old_value': 253.615},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][14]['area']": {'new_value': 10.0,
                                                                                           'old_value': 360.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][14]['depth_min']": {'new_value': 10.0,
                                                                                                'old_value': 255.44},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][1]['area']": {'new_value': 10.0,
                                                                                          'old_value': 107.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][1]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 195.36},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][2]['area']": {'new_value': 10.0,
                                                                                          'old_value': 122.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][2]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 195.68},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][3]['area']": {'new_value': 10.0,
                                                                                          'old_value': 94.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][3]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 195.68},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][4]['area']": {'new_value': 10.0,
                                                                                          'old_value': 199.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][4]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 195.68},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][5]['area']": {'new_value': 10.0,
                                                                                          'old_value': 176.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][5]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 212.62},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][6]['area']": {'new_value': 10.0,
                                                                                          'old_value': 151.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][6]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 213.525},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][7]['area']": {'new_value': 10.0,
                                                                                          'old_value': 90.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][7]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 214.165},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][8]['area']": {'new_value': 10.0,
                                                                                          'old_value': 158.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][8]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 215.415},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][9]['area']": {'new_value': 10.0,
                                                                                          'old_value': 163.0},
        "root['samples'][0]['acquisitions'][0]['processings'][0]['objects'][9]['depth_min']": {'new_value': 10.0,
                                                                                               'old_value': 215.76},
        "root['samples'][0]['sampledatetime']": {'new_value': '20200208-111218', 'old_value': '20200205-111218'},
        "root['samples'][0]['ship']": {'new_value': 'sagitta4', 'old_value': 'sagitta3'}}
