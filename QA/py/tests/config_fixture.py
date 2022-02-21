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
sys.path.extend([join("", "..", "..", "py")])

HERE = Path(dirname(realpath(__file__)))

from DB.helpers.DBWriter import DBWriter
from BO.TSVFile import TSVFile
from FS.Vault import Vault
from API_operations.exports.ForProject import ProjectExport


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
    # Empty Vault
    vault = Vault((HERE / 'vault').as_posix())
    shutil.rmtree(vault.sub_path("0000"), ignore_errors=True)
    # env variable to conf
    os.environ["APP_CONFIG"] = (HERE / 'config.ini').as_posix()
    yield conf
    # Teardown
    conf.cleanup()
