# Fixture for monkey-patching fastapi
# So that no token validation occurs, user ID is in security token
from os.path import dirname, realpath
from pathlib import Path
from os import path

import pytest

HERE = Path(dirname(realpath(__file__)))


# noinspection PyProtectedMember
@pytest.fixture(scope="session")
def fastapi_noauth() -> None:
    # Setup
    # Patch the paths to link.ini
    from helpers import link_to_legacy
    link_to_legacy.INI_DIR = HERE
    link_to_legacy.INI_FILE = path.join(HERE, "link.ini")
    # Overwrite a method in URLSafeTimedSerializer
    from helpers import fastApiUtils
    fastApiUtils._build_serializer()
    sav_loads = fastApiUtils._serializer.loads
    fastApiUtils._serializer.loads = lambda s, max_age: {"user_id": s}
    yield
    # Teardown
    # Just for completeness as the process is being shut down
    fastApiUtils._serializer.loads = sav_loads
