# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from DB.Acquisition import Acquisition
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample
from DB.Task import Task
from DB.Taxonomy import Taxonomy
from DB.User import User, Role
from DB.ProjectPrivilege import ProjectPrivilege


def test_to_str():
    """Just to ensure there is no type in __str__ methods"""
    assert str(Acquisition()) is not None
    assert str(Process()) is not None
    assert str(Project()) is not None
    assert str(Sample()) is not None
    assert str(Task()) is not None
    assert str(Taxonomy()) is not None
    assert str(User()) is not None
    assert str(Role()) is not None
    assert str(ProjectPrivilege()) is not None
