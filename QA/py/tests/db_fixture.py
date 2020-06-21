# Fixture for ensuring we have the DB up and running
from os.path import dirname, realpath
from pathlib import Path

import pytest

from tools.dbBuildSQL import EcoTaxaDBFrom0, EcoTaxaExistingDB

HERE = Path(dirname(realpath(__file__)))
PG_DIR = HERE / ".." / "pg_files"
CONF_FILE = HERE / "appli" / "config.cfg"


@pytest.fixture(scope="module")
def database() -> EcoTaxaDBFrom0:
    # Setup
    db = EcoTaxaDBFrom0(PG_DIR, CONF_FILE)
    db.create()
    yield db
    # Teardown
    db.cleanup()


@pytest.fixture(scope="module")
def filled_database() -> EcoTaxaDBFrom0:
    # Setup
    db = EcoTaxaExistingDB()
    db.write_config(CONF_FILE, "localhost", 5434)
    yield db
    # Teardown
