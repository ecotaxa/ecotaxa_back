# Fixture for monkey-patching fastapi
# So that no token validation occurs, user ID is in security token
import logging, os
from typing import Any, Generator

# We need this before first import of main.py for location middleware
FAKE_SERVER = "https://my.real.site:443/"
os.environ["SERVERURL"] = FAKE_SERVER

import pytest
from BG_operations.JobScheduler import JobScheduler
from fastapi.testclient import TestClient

# from starlette.testclient import TestClient

from tests.jobs import clear_all_jobs
from tests.prj_utils import sce_check_consistency


# noinspection PyProtectedMember
# Note: We need this fixture in 99% of the tests, so it could be "session" scoped,
# but the remaining 1% AKA test_login.py fails due to below security patch
@pytest.fixture(scope="module")
def fastapi(config, database, tstlogs) -> Generator[TestClient, Any, None]:
    # Overwrite a method in URLSafeTimedSerializer
    from helpers import fastApiUtils
    import main

    fastApiUtils.build_serializer()
    main.logger.setLevel(logging.CRITICAL)
    sav_loads = fastApiUtils._serializer.loads
    fastApiUtils._serializer.loads = lambda s, max_age: {"user_id": s}

    client = TestClient(main.app)
    main.JOB_INTERVAL = 0.01
    with client:  # Trigger the fastapi 'startup' event -> launches the JobScheduler
        yield client
    # Teardown, once per module
    consistency_exception = None
    try:
        # Note: if it fails here, add ccheck fixture to all tests in module and
        # track the faulty one
        sce_check_consistency("fastapi fx")
    except AssertionError as e:
        consistency_exception = e
    fastApiUtils._serializer.loads = sav_loads
    JobScheduler.shutdown()
    if consistency_exception is not None:
        clear_all_jobs()  # Don't leak failed/unfinished jobs to next tests
        raise consistency_exception
