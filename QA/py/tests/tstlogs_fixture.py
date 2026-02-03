#
# A log directory for tests, not the app ones
#
import os
import shutil
from os.path import dirname, realpath
from pathlib import Path
from typing import Any, Generator

import pytest

HERE = Path(dirname(realpath(__file__)))
LOGS = HERE.parent / "test_logs"

import contextlib
import os


@contextlib.contextmanager
def pushd(self):
    previous_dir = os.getcwd()
    os.chdir(self)
    try:
        yield
    finally:
        os.chdir(previous_dir)


@pytest.fixture(scope="session")
def tstlogs() -> Generator[Path, Any, None]:
    shutil.rmtree(LOGS, ignore_errors=True)
    os.mkdir(LOGS)
    yield LOGS
    # Teardown
    pass
