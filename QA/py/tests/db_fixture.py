# Fixture for ensuring we have the DB up and running
from os.path import dirname, realpath
from pathlib import Path

import pytest

from tests.prj_utils import sce_check_consistency
from tools.dbBuildSQL import EcoTaxaDBFrom0, EcoTaxaExistingDB

HERE = Path(dirname(realpath(__file__)))
PG_DIR = HERE / ".." / "pg_files"
CONF_FILE = HERE / "config.ini"


@pytest.fixture(scope="session")
def database(config) -> EcoTaxaDBFrom0:
    # Setup
    db = EcoTaxaDBFrom0(PG_DIR, CONF_FILE)
    db.create()
    yield db
    # Teardown
    sce_check_consistency("db fx")
    db.cleanup()


@pytest.fixture(scope="session")
def filled_database(config) -> EcoTaxaDBFrom0:
    # Setup
    db = EcoTaxaExistingDB()
    db.write_config(CONF_FILE, "localhost", 5434)
    yield db
    # Teardown


@pytest.fixture(scope="function")
def ccheck():
    # Setup
    yield
    # Teardown
    sce_check_consistency("ccheck fx")
