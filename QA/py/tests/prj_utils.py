from API_operations.Consistency import ProjectConsistencyChecker
from API_operations.admin.NightlyJob import NightlyJobService, logger
from API_operations.helpers.Service import Service

from tests.credentials import ADMIN_USER_ID
from tests.tstlogs_fixture import pushd


def check_project(tstlogs, prj_id: int):
    with pushd(tstlogs):
        with ProjectConsistencyChecker(prj_id) as sce:
            problems = sce.run(ADMIN_USER_ID)
        assert problems == [], problems


def sce_check_consistency(from_):
    sce = NightlyJobService()
    sce.update_progress = lambda *args: None
    with sce:
        old_logger = logger.info
        logger.info = lambda *args: print(from_, args[0] % args[1:])
        assert sce.check_consistency(0, 0, True)
        logger.info = old_logger
