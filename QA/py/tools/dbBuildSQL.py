"""
Build the DB from scratch in EcoTaxa V2_2, using an SQL Dump, so the 2_2 source tree is not needed.
"""
import shutil
import sys
from os import environ
from os.path import join
from pathlib import Path

from lib.processes import SyncSubProcess

psql_bin = "psql"
# If we already have a server don't create one, e.g. in GitHub action
PG_HOST = environ.get("POSTGRES_HOST")
PG_PORT = environ.get("POSTGRES_PORT")
if PG_HOST and PG_PORT:
    PG_PORT = int(PG_PORT)
else:
    pg_lib = "/usr/lib/postgresql/12/bin/"
    pgctl_bin = join(pg_lib, "pg_ctl")
    initdb_bin = join(pg_lib, "initdb")
    mustExist = [pgctl_bin, initdb_bin]
    for aFile in mustExist:
        if not Path(aFile).exists():
            print("File/directory %s not found where expected" % aFile)
            sys.exit(-1)
    PG_PORT = 5440

# noinspection SqlResolve,SqlNoDataSourceInspection
CREATE_DB_SQL = """
create DATABASE ecotaxa
WITH ENCODING='LATIN1'
OWNER=postgres
TEMPLATE=template0 LC_CTYPE='C' LC_COLLATE='C' CONNECTION LIMIT=-1;
"""


class EcoTaxaDB(object):

    def __init__(self, dbdir: Path):
        self.db_dir = dbdir.resolve()
        self.data_dir = self.db_dir / "Data"
        self.pwd_file = self.db_dir / "pg_pwd.txt"
        self.schema_creation_file = self.db_dir / "schem_prod.sql"

    def get_env(self):
        # Return the environment for postgres subprocesses
        ret = {"PGDATA": self.data_dir,
               "PGDATABASE": "ecotaxa",
               "PGLOG": self.db_dir / "log.txt"
               }
        return ret

    def init(self):
        # Create data files
        pg_opts = ['-U', 'postgres', '-A', 'trust', '-E', 'Latin1', '--locale=C', '--pwfile=%s' % self.pwd_file]
        cmd = [initdb_bin] + pg_opts
        SyncSubProcess(cmd, env=self.get_env())

    def launch(self):
        # Produce connection sockets in a user-writable directory (linux)
        pg_opts = ['-o', '-c unix_socket_directories="' + str(self.db_dir / "run") + '"']
        pg_opts += ['-o', '"-p %d"' % PG_PORT]
        cmd = [pgctl_bin, "start", "-W"] + pg_opts
        # Cook an environment for the subprocess
        # we do NOT use os.environ in order not to pollute current process
        # Note: the process dies right away as pgctl launches a daemon
        SyncSubProcess(cmd, env=self.get_env())
        # TODO: proper wait
        import time
        time.sleep(2)

    def ddl(self, host, password):
        # -h localhost force use of TCP/IP socket, otherwise psql tries local pipes in /var/run
        env = {'PGPASSWORD': password}
        pg_opts = ['-U', 'postgres', '-h', host, '-p', "%d" % PG_PORT]
        cre_opts = ['-c', CREATE_DB_SQL]
        cmd = [psql_bin] + pg_opts + cre_opts
        SyncSubProcess(cmd, env=env)
        #
        schem_opts = ['-d', 'ecotaxa', '-f', self.schema_creation_file]
        cmd = [psql_bin] + pg_opts + schem_opts
        SyncSubProcess(cmd, env=env)

    def create(self):
        if not (PG_HOST and PG_PORT):
            self.init()
            self.launch()
            # TODO: Password is ignored in this context
            self.ddl('localhost', 'postgres12')
        else:
            self.ddl(PG_HOST, 'postgres12')

    def cleanup(self):
        # Remove data files
        if not (PG_HOST and PG_PORT):
            shutil.rmtree(self.data_dir)
        else:
            # Server should do the cleanup, e.g. exit docker
            pass
