#
# E.g. use: 'austin' statistical profiler for python
# Also need flamegraph.pl from https://raw.githubusercontent.com/brendangregg/FlameGraph/master/flamegraph.pl
#
# PYTHONPATH=..:../../../py austin ../venv/bin/python3 perf_export.py | ./flamegraph.pl --countname=usec > process_export.svg
#
from tests.db_fixture import CONF_FILE
from API_operations.exports.EMODnet import EMODnetExport
from DB.helpers.DBWriter import DBWriter
from BO.TSVFile import TSVFile

import logging
logging.basicConfig(level=logging.INFO)

from tools.dbBuildSQL import EcoTaxaExistingDB


def main():
    EcoTaxaExistingDB.write_config(CONF_FILE, "localhost", 5434)
    DBWriter.SEQUENCE_CACHE_SIZE = 5
    TSVFile.REPORT_EVERY = 5
    src = EMODnetExport(99,False,True)
    src.run(760)


if __name__ == '__main__':
    main()
