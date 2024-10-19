# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Wrapper over various date & time functions, which can be mocked for testing.
#
from datetime import datetime, timezone


def _now_time():
    # We patch this one during tests.
    return datetime.now(timezone.utc)


def now_time() -> datetime:
    """Single client-side present time source, returns a UTC datetime.
    Note: During tests, we can fix the time by overriding _now_time() above."""
    return _now_time()
