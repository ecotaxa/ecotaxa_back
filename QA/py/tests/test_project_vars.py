# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from copy import deepcopy

from starlette import status
import pytest
from BO.ProjectVars import ProjectVar
from BO.Vocabulary import *
from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import do_import, BAD_FREE_DIR, create_project
from tests.test_update_prj import PROJECT_UPDATE_URL


def test_error_var():
    # A typo in the formula
    with pytest.raises(TypeError) as e_info:
        _myvar = ProjectVar("4.0/3.0*",
                            Vocabulary.biovolume,
                            Units.cubic_millimetres_per_cubic_metre)


def test_empty_var():
    # Various "nothing"s
    for a_val in (None, ""):
        with pytest.raises(TypeError) as e_info:
            _myvar = ProjectVar(a_val,
                                Vocabulary.biovolume,
                                Units.cubic_millimetres_per_cubic_metre)


def test_parse_expr():
    expr = "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3+Unexpanded+w3ird"
    vars = ProjectVar.find_vars(expr)
    assert vars == ['Unexpanded', 'math.pi', 'math.sqrt', 'obj.area', 'ssm.pixel_size', 'w3ird']


BODC_VARS_KEY = "bodc_variables"


def test_project_vars(config, database, fastapi, caplog):
    prj_id = create_project(ADMIN_USER_ID, "Stored Vars", "CPICS")
    do_import(prj_id, BAD_FREE_DIR, ADMIN_USER_ID)
    # Do like in legacy app, i.e. fetch/modify/resend
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    read_json = rsp.json()
    assert BODC_VARS_KEY in read_json
    upd_json = deepcopy(read_json)

    # Bad update with non-dict
    upd_json[BODC_VARS_KEY] = "toto"
    url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, rsp.reason + str(rsp.content)
    # Good format update with nothing
    vars = {}
    upd_json[BODC_VARS_KEY] = vars
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == status.HTTP_200_OK, rsp.reason + str(rsp.text)
    # Good format update with bad keys
    vars["e"] = 1
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, rsp.reason + str(rsp.text)
    # Good format update with good key
    del vars["e"]
    vars["subsample_coef"] = "1/sub_part"
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == status.HTTP_200_OK, rsp.reason + str(rsp.text)
    # Good format update with good key but no val
    vars["subsample_coef"] = "  "
    vars["individual_volume"] = " "
    vars["total_water_volume"] = None
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == status.HTTP_200_OK, rsp.reason + str(rsp.text)
    # Syntax error in formula
    vars["subsample_coef"] = "1/toto tutu"
    rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, rsp.reason + str(rsp.text)
    # TODO: Unknown col in formula
    # vars["subsample_coef"] = "1/sup_part"
    # rsp = fastapi.put(url, headers=ADMIN_AUTH, json=upd_json)
    # assert rsp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, rsp.reason + str(rsp.text)
