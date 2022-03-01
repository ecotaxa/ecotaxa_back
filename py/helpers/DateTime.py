# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Wrapper over various date & time functions, which can be mocked for testing.
#
import datetime


def _now_time():
    # We patch this one during tests.
    return datetime.datetime.now()


def now_time() -> datetime.datetime:
    # During test, sometimes this def is imported before the test, so it cannot be patched.
    return _now_time()
