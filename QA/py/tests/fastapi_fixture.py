# Fixture for monkey-patching fastapi
# So that no token validation occurs, user ID is in security token
from os.path import dirname, realpath
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from BG_operations.JobScheduler import JobScheduler

import pytest

HERE = Path(dirname(realpath(__file__)))

client = TestClient(app)


# noinspection PyProtectedMember
@pytest.fixture(scope="function")
def fastapi() -> TestClient:
    # Overwrite a method in URLSafeTimedSerializer
    from helpers import fastApiUtils

    fastApiUtils.build_serializer()
    sav_loads = fastApiUtils._serializer.loads
    fastApiUtils._serializer.loads = lambda s, max_age: {"user_id": s}
    with client:
        yield client
    # Teardown
    # Just for completeness as the process is being shut down
    fastApiUtils._serializer.loads = sav_loads
    assert JobScheduler.is_sane_on_shutdown()
