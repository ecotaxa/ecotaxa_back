# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Wrapper over various date & time functions, which can be mocked for testing.
#
import datetime


def now_time():
    return datetime.datetime.now()
