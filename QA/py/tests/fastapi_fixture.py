# Fixture for monkey-patching fastapi
# So that no token validation occurs, user ID is in security token
from os.path import dirname, realpath
from pathlib import Path
from os import path

import pytest

HERE = Path(dirname(realpath(__file__)))

@pytest.fixture(scope="session")
def fastapi_noauth() -> None:
    # Setup
    from helpers import fastApiUtils
    # Overwrite a method in URLSafeTimedSerializer
    sav_loads = fastApiUtils.serializer.loads
    fastApiUtils.serializer.loads = lambda s, max_age: {"user_id": s}
    # Patch the paths to link.ini
    from helpers import link_to_legacy
    link_to_legacy.INI_DIR = HERE
    link_to_legacy.INI_FILE = path.join(HERE, "link.ini")
    yield
    # Teardown
    # Just for completeness as the process is being shut down
    fastApiUtils.serializer.loads = sav_loads
