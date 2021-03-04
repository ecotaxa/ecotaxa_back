# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import pytest
from BO.ProjectVars import ProjectVar
from BO.Vocabulary import *


# Import services

def test_error_var():
    # A typo in the formula
    with pytest.raises(TypeError) as e_info:
        _myvar = ProjectVar("4.0/3.0*",
                           Vocabulary.biovolume,
                           Units.cubic_millimetres_per_cubic_metre)
