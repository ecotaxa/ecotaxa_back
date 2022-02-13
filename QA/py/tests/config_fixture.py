#
# In ordinary operation mode, we read configuration from V2_2 directory.
# For testing, as we create a DB from scratch using SQL and don't need V2_2 anymore, we break the
# virtual link b/w the 2 codebases.
#
import shutil
import sys
from os.path import join, dirname, realpath
from pathlib import Path

import pytest

# Import services under test as a library
sys.path.extend([join("", "..", "..", "py")])

HERE = Path(dirname(realpath(__file__)))
TEST_CONFIG = HERE / "link.ini"

# Import setup point
import helpers.link_to_legacy as link
from DB.helpers.DBWriter import DBWriter
from BO.TSVFile import TSVFile
from FS.Vault import Vault
from API_operations.exports.ForProject import ProjectExport

class EcoTaxaConfig(object):
    def cleanup(self):
        pass


@pytest.fixture(scope="session")
def config() -> EcoTaxaConfig:
    # Setup by injecting values inside the app 'link' module
    link.INI_DIR = HERE
    link.INI_FILE = TEST_CONFIG
    conf = EcoTaxaConfig()
    # Inject low values for covering, even with test small dataset
    DBWriter.SEQUENCE_CACHE_SIZE = 5
    TSVFile.REPORT_EVERY = 5
    ProjectExport.ROWS_REPORT_EVERY = 5
    ProjectExport.IMAGES_REPORT_EVERY = 7
    # Empty Vault
    vault = Vault(join(link.read_link(), 'vault'))
    shutil.rmtree(vault.sub_path("0000"), ignore_errors=True)
    yield conf
    # Teardown
    conf.cleanup()
