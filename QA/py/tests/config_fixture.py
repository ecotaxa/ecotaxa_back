#
# In ordinary operation mode, we read configuration from V2_2 directory.
# For testing, as we create a DB from scratch using SQL and don't need V2_2 anymore, we break the
# virtual link b/w the 2 codebases.
#
import sys
from os.path import join, dirname, realpath
from pathlib import Path

import pytest

# Import services under test as a library
sys.path.extend([join("", "..", "..", "py")])

HERE = Path(dirname(realpath(__file__)))
TEST_CONFIG = HERE / "link.ini"

# Import setup point
import link


class EcoTaxaConfig(object):
    def cleanup(self):
        pass


@pytest.fixture(scope="module")
def config() -> EcoTaxaConfig:
    # Setup
    link.INI_DIR = HERE
    link.INI_FILE = TEST_CONFIG
    conf = EcoTaxaConfig()
    yield conf
    # Teardown
    conf.cleanup()
