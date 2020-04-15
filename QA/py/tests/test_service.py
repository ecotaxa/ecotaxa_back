# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict

import pytest
from framework.Service import BaseService


class TestService(BaseService):
    my_param: int = 0
    """ The input param 1"""
    my_dict: Dict = {'e': 5}
    MSG_IN = {"p1": id(my_param),
              "p2": id(my_dict),
              }

    def run(self):
        self.my_param += 10
        self.my_dict["+"] = "foo"


def test_service():
    req = {"p1": 6, "p2": {"-": "bar"}}
    rsp = TestService.call(req)
    assert rsp["p1"] == 16
    assert len(rsp["p2"]) == 2


# def test_typo_service():
#     req = {"p1": 6, "typo": 5}
#     with pytest.raises(Exception):
#         TestService.call(req)

class SubService(TestService):
    SUP = TestService
    MSG_IN = {"p1": id(SUP.my_param),
              "p2": id(SUP.my_dict),
              }

def test_service2():
    req = {"p1": 6, "p2": {"-": "bar"}}
    rsp = SubService.call(req)
    assert rsp["p1"] == 16
    assert len(rsp["p2"]) == 2


