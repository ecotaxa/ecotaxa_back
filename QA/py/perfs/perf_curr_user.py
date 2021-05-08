#
# E.g. use: 'austin' statistical profiler for python
# Also need flamegraph.pl from https://raw.githubusercontent.com/brendangregg/FlameGraph/master/flamegraph.pl
#
# PYTHONPATH=..:../../../py austin ../../venv/bin/python3 perf_curr_user.py | ./flamegraph.pl --countname=usec > curr_user.svg
#
import logging

from API_operations.CRUD.Users import *
from BO.Rights import *
from helpers.Timer import *

from tests.credentials import ADMIN_USER_ID
from tests.db_fixture import CONF_FILE

logging.basicConfig(level=logging.INFO)

from tools.dbBuildSQL import EcoTaxaExistingDB

from logging import getLogger

logger = getLogger()


def main():
    EcoTaxaExistingDB.write_config(CONF_FILE, "localhost", 5434)
    current_user_id = ADMIN_USER_ID
    loops = 10000
    with CodeTimer("%d get user " % loops, logger) as tim:
        for i in range(loops):
            with UserService() as sce:
                ret = sce.search_by_id(current_user_id, current_user_id)
                # assert ret is not None
                # # noinspection PyTypeHints
                # ret.can_do = RightsBO.allowed_actions(ret)  # type:ignore
                # # noinspection PyTypeHints
                # ret.last_used_projects = Preferences(ret).recent_projects(session=sce.session)  # type:ignore


if __name__ == '__main__':
    main()
