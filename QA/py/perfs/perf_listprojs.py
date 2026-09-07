#
# E.g. use: 'austin' statistical profiler for python
# Also need flamegraph.pl from https://raw.githubusercontent.com/brendangregg/FlameGraph/master/flamegraph.pl
#
# PYTHONPATH=..:../../../py austin ../../venv/bin/python3 perf_listprojs.py | ./flamegraph.pl --countname=usec > list_proj.svg
#
# Austin is broken in 4.0, new method:
#
# PYTHONPATH=..:../../../py /home/laurent/Devs/from_Lab/ecotaxa_back/QA/venv314/bin/python -m cProfile -o mon_profil.pstats perf_listprojs.py; pyprof2calltree -i mon_profil.pstats -o callgrind.out; kcachegrind callgrind.out
#
import gc
import logging
import time

from API_operations.CRUD.Projects import *

from tests.credentials import ADMIN_USER_ID
from tests.db_fixture import CONF_FILE

logging.basicConfig(level=logging.INFO)

from tools.dbBuildSQL import EcoTaxaExistingDB


def main():
    EcoTaxaExistingDB.write_config(CONF_FILE, "localhost", 5432)
    n = 40
    with ProjectsService() as sce:
        pass  # Heat up
    # gc.disable() # Uncomment for flat results, GC takes LOTS of time as we allocate just for the test
    t0 = time.time()
    for i in range(0, n):
        with ProjectsService() as sce:
            ret = sce.search(current_user_id=760)
    t1 = time.time()
    print(f"{n} searches in {t1-t0:.3f}s, i.e. {(t1-t0)/n:.3f}s per search")


if __name__ == "__main__":
    main()
