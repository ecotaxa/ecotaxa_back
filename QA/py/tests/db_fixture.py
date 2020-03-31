# Fixture for ensuring we have the DB up and running
from os.path import dirname, realpath
from pathlib import Path

import pytest

from tools.dbBuildSQL import EcoTaxaDB

HERE = Path(dirname(realpath(__file__)))
PG_DIR = HERE / ".." / "pg_files"


@pytest.fixture(scope="module")
def database() -> EcoTaxaDB:
    # Setup
    db = EcoTaxaDB(PG_DIR)
    db.create()
    yield db
    # Teardown
    db.cleanup()

