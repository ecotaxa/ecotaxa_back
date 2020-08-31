#
# E.g. use: 'austin' statistical profiler for python
# Also need flamegraph.pl from https://raw.githubusercontent.com/brendangregg/FlameGraph/master/flamegraph.pl
#
# PYTHONPATH=..:../../../py austin ../../venv/bin/python3 perf_subset.py | ./flamegraph.pl --countname=usec > process_subset.svg
#
from tests.db_fixture import CONF_FILE
from API_models.crud import *
from API_models.subset import *
from API_operations.Subset import *
from API_operations.CRUD import *
from API_operations.CRUD.Tasks import TaskService
from API_operations.CRUD.Projects import *

import logging
logging.basicConfig(level=logging.INFO)

from tools.dbBuildSQL import EcoTaxaExistingDB


def main():
    EcoTaxaExistingDB.write_config(CONF_FILE, "localhost", 5434)
    # Old project with 1,2M images
    src_prj_id = 152
    task_id = TaskService().create()
    prj_id = ProjectsService().create(1, CreateProjectReq(title="Test LS"))
    req = SubsetReq(task_id=task_id,
                    filters={},
                    dest_prj_id=prj_id,
                    limit_type='P',
                    limit_value=6,
                    do_images=False)
    SubsetService(src_prj_id, req=req).run()


if __name__ == '__main__':
    main()
