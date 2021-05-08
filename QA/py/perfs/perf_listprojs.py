#
# E.g. use: 'austin' statistical profiler for python
# Also need flamegraph.pl from https://raw.githubusercontent.com/brendangregg/FlameGraph/master/flamegraph.pl
#
# PYTHONPATH=..:../../../py austin ../../venv/bin/python3 perf_listprojs.py | ./flamegraph.pl --countname=usec > list_proj.svg
#
import logging

from API_operations.CRUD.Projects import *

from tests.credentials import ADMIN_USER_ID
from tests.db_fixture import CONF_FILE

logging.basicConfig(level=logging.INFO)

from tools.dbBuildSQL import EcoTaxaExistingDB


def main():
    EcoTaxaExistingDB.write_config(CONF_FILE, "localhost", 5434)
    with ProjectsService() as sce:
        sce.search(current_user_id=ADMIN_USER_ID)


if __name__ == '__main__':
    main()
