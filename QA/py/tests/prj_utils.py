from API_operations.Consistency import ProjectConsistencyChecker

from tests.credentials import ADMIN_USER_ID
from tests.tstlogs_fixture import pushd


def check_project(tstlogs, prj_id: int):
    with pushd(tstlogs):
        with ProjectConsistencyChecker(prj_id) as sce:
            problems = sce.run(ADMIN_USER_ID)
        assert problems == [], problems
