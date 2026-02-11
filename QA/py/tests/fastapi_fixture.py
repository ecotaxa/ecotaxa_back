# Fixture for monkey-patching fastapi
# So that no token validation occurs, user ID is in security token
import logging
from typing import Any, Generator

import main
import pytest
from BG_operations.JobScheduler import JobScheduler
from fastapi.testclient import TestClient

from tests.jobs import clear_all_jobs
from tests.prj_utils import sce_check_consistency

client = TestClient(main.app)


# noinspection PyProtectedMember
# Note: We need this fixture in 99% of the tests, so it could be "session" scoped,
# but the remaining 1% AKA test_login.py fails due to below security patch
@pytest.fixture(scope="module")
def fastapi(config, database, tstlogs) -> Generator[TestClient, Any, None]:
    # Overwrite a method in URLSafeTimedSerializer
    from helpers import fastApiUtils

    fastApiUtils.build_serializer()
    sav_loads = fastApiUtils._serializer.loads
    fastApiUtils._serializer.loads = lambda s, max_age: {"user_id": s}
    main.JOB_INTERVAL = 0.01
    with client:  # Trigger the fastapi 'startup' event -> launches the JobScheduler
        yield client
    # Teardown, once per module
    consistency_exception = None
    try:
        sce_check_consistency("fastapi fx")
    except AssertionError as e:
        consistency_exception = e
    fastApiUtils._serializer.loads = sav_loads
    JobScheduler.shutdown()
    if consistency_exception is not None:
        clear_all_jobs()  # Don't leak failed/unfinished jobs to next tests
        raise consistency_exception
