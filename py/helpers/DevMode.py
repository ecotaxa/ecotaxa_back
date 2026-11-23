# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Helpers for detecting development and debug execution modes.
#
import os
import sys


def is_dev_mode() -> bool:
    """Return True when running in development mode (launched via uvicorn)."""
    return "uvicorn" in sys.argv


def is_debug_mode() -> bool:
    """Return True when running under a Python debugger/tracer."""
    return sys.gettrace() is not None


def is_local_https_url(url: str) -> bool:
    """Return True when the URL points to a local HTTPS endpoint (e.g. self-signed dev)."""
    return url.startswith("https://localhost")


def is_pytest():
    return "PYTEST_CURRENT_TEST" in os.environ
