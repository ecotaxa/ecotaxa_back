#
# For testing, we create a DB from scratch using python build
#
import os
import shutil
import sys
from os.path import join, dirname, realpath
from pathlib import Path

import pytest

# Import services under test as a library
# TODO: Not here
sys.path.extend([join("", "..", "..", "py")])

HERE = Path(dirname(realpath(__file__)))

from DB.helpers.DBWriter import DBWriter
from BO.TSVFile import TSVFile
from FS.Vault import Vault
from API_operations.exports.ForProject import ProjectExport
from API_operations.admin.NightlyJob import NightlyJobService


class EcoTaxaConfig(object):
    def cleanup(self):
        pass


@pytest.fixture(scope="session")
def config() -> EcoTaxaConfig:
    conf = EcoTaxaConfig()
    # Inject low values for covering, even with test small dataset
    DBWriter.SEQUENCE_CACHE_SIZE = 5
    TSVFile.REPORT_EVERY = 5
    ProjectExport.ROWS_REPORT_EVERY = 5
    ProjectExport.IMAGES_REPORT_EVERY = 7
    NightlyJobService.REPORT_EVERY = 2
    # Empty Vault
    vault = Vault((HERE / "vault").as_posix())
    shutil.rmtree(vault.path.joinpath("0000").as_posix(), ignore_errors=True)
    # env variable to conf
    os.environ["APP_CONFIG"] = (HERE / "config.ini").as_posix()
    yield conf
    # Teardown
    conf.cleanup()
