"""
Build the DB from scratch in EcoTaxa V2_2, using an SQL Dump, so the 2_2 source tree is not needed.
"""
import shutil
import sys
import time
from os import environ
from os.path import join, dirname, realpath
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

import socket


def is_port_opened(host: str, port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0


class EcoTaxaExistingDB(object):
    """
        For running tests onto an existing instance.
    """
    def write_config(self, conf_file: Path, host: str, port: int):
        with open(str(conf_file), "w") as f:
            f.write(EcoTaxaDBFrom0.CONF % (host, port))


class EcoTaxaDBFrom0(object):

    def __init__(self, dbdir: Path, conffile: Path):
        self.db_dir = dbdir.resolve()
        self.data_dir = self.db_dir / "Data"
        self.pwd_file = self.db_dir / "pg_pwd.txt"
        self.schema_creation_file = self.db_dir / "schem_prod.sql"
        self.conf_file = conffile

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

    def launch(self, host):
        # Produce connection sockets in a user-writable directory (linux)
        pg_opts = ['-o', '-c unix_socket_directories="' + str(self.db_dir / "run") + '"']
        pg_opts += ['-o', '"-p %d"' % PG_PORT]
        cmd = [pgctl_bin, "start", "-W"] + pg_opts
        # Cook an environment for the subprocess
        # we do NOT use os.environ in order not to pollute current process
        # Note: the process dies right away as pgctl launches a daemon
        SyncSubProcess(cmd, env=self.get_env(), out_file="postgres_start.log")
        # Wait until the server port is opened
        while not is_port_opened(host, PG_PORT):
            time.sleep(0.5)

    def shutdown(self, host:str):
        # Stop command
        cmd = [pgctl_bin, "stop", "-D", self.data_dir]
        # Cook an environment for the subprocess
        SyncSubProcess(cmd, env=self.get_env(), out_file="postgres_stop.log")
        # Wait until the server port is closed
        while is_port_opened(host, PG_PORT):
            time.sleep(0.5)

    def ddl(self, host, password):
        # -h localhost force use of TCP/IP socket, otherwise psql tries local pipes in /var/run
        env = {'PGPASSWORD': password}
        pg_opts = ['-U', 'postgres', '-h', host, '-p', "%d" % PG_PORT]
        cre_opts = ['-c', CREATE_DB_SQL]
        cmd = [psql_bin] + pg_opts + cre_opts
        SyncSubProcess(cmd, env=env, out_file="db_create.log")
        #
        schem_opts = ['-d', 'ecotaxa', '-f', self.schema_creation_file]
        cmd = [psql_bin] + pg_opts + schem_opts
        SyncSubProcess(cmd, env=env, out_file="db_build.log")

    def create(self):
        if not (PG_HOST and PG_PORT):
            host = 'localhost'
            self.init()
            self.launch(host)
            # TODO: Password (in call to self.ddl) is ignored in this context
        else:
            host = PG_HOST
        self.ddl(host, 'postgres12')
        self.write_config(host)

    CONF = """
DB_USER="postgres"
DB_PASSWORD="postgres12"
DB_HOST="%s"
DB_PORT="%d"
DB_DATABASE="ecotaxa"
THUMBSIZELIMIT=99
    """

    def write_config(self, host):
        with open(str(self.conf_file), "w") as f:
            f.write(self.CONF % (host, PG_PORT))

    def cleanup(self):
        # Remove data files
        if not (PG_HOST and PG_PORT):
            self.shutdown('localhost')
            shutil.rmtree(self.data_dir, ignore_errors=True)
        else:
            # Server should do the cleanup, e.g. exit docker
            pass


if __name__ == '__main__':
    HERE = Path(dirname(realpath(__file__)))
    PG_DIR = HERE / ".." / "pg_files"
    db = EcoTaxaDBFrom0(PG_DIR, Path("fakeconf"))
    try:
        db.cleanup()
    except FileNotFoundError:
        pass
    db.create()
