# Fixture for monkey-patching fastapi
# So that no token validation occurs, user ID is in security token

import main
import pytest
from BG_operations.JobScheduler import JobScheduler
from fastapi.testclient import TestClient

from tests.prj_utils import sce_check_consistency

client = TestClient(main.app)


# noinspection PyProtectedMember
# Note: We need this fixture in 99% of the tests, so it could be "session" scoped,
# but the remaining 1% AKA test_login.py fails due to below security patch
@pytest.fixture(scope="module")
def fastapi(config, database, tstlogs) -> TestClient:
    # Overwrite a method in URLSafeTimedSerializer
    from helpers import fastApiUtils

    fastApiUtils.build_serializer()
    sav_loads = fastApiUtils._serializer.loads
    fastApiUtils._serializer.loads = lambda s, max_age: {"user_id": s}
    main.JOB_INTERVAL = 0.05
    with client:  # Trigger the fastapi 'startup' event -> launches the JobScheduler
        yield client
    # Teardown, once per module
    sce_check_consistency("fastapi fx")
    fastApiUtils._serializer.loads = sav_loads
    JobScheduler.shutdown()
