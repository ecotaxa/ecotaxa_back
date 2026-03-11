"""
Build the DB from scratch in EcoTaxa.
"""

import os
import shutil
import socket
import sys
import time
from os import environ
from os.path import join, dirname, realpath
from pathlib import Path

from lib.processes import SyncSubProcess
from tests.test_import import SHARED_DIR, FTP_DIR, TEST_DIR

psql_bin = "psql"
# If we already have a server don't create one, e.g. in GitHub action
PG_HOST = environ.get("POSTGRES_HOST")
PG_PORT = environ.get("POSTGRES_PORT")


if PG_HOST and PG_PORT:
    PG_PORT = int(PG_PORT)
else:
    pg_lib = "/usr/lib/postgresql/14/bin/"  # ============ 124 passed, 1 skipped, 4 warnings in 221.91s (0:03:41) ============
    pgctl_bin = join(pg_lib, "pg_ctl")
    initdb_bin = join(pg_lib, "initdb")
    mustExist = [pgctl_bin, initdb_bin]
    for aFile in mustExist:
        if not Path(aFile).exists():
            print("File/directory %s not found where expected" % aFile)
            sys.exit(-1)
    PG_PORT = 5440


def is_port_opened(host: str, port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0


class EcoTaxaExistingDB(object):
    """
    For running tests onto an existing instance.
    """

    @staticmethod
    def write_config(
        conf_file: Path,
        host: str,
        port: int,
        vault: str = "/tmp",
        jobs: str = "/tmp",
        shared: str = "/tmp",
        ftp: str = "/tmp",
        models: str = "/tmp",
        usersfilesarea="/tmp",
    ):
        with open(str(conf_file), "w") as f:
            f.write(
                EcoTaxaDBFrom0.CONF
                % (
                    host,
                    port,
                    host,
                    port,
                    vault,
                    jobs,
                    shared,
                    ftp,
                    models,
                    usersfilesarea,
                )
            )
        os.environ["APP_CONFIG"] = conf_file.absolute().as_posix()


DB_NAME = "ecotaxa"
DB_PASSWORD = "postgres12"


class EcoTaxaDBFrom0(object):
    def __init__(self, dbdir: Path, conffile: Path):
        self.db_dir = dbdir.resolve()
        self.data_dir = self.db_dir / "Data"
        self.pwd_file = self.db_dir / "pg_pwd.txt"
        self.v22_schema_creation_file = self.db_dir / "schem_prod.sql"
        self.schema_upgrade_file = self.db_dir / "upgrade_prod.sql"
        self.data_load_file = self.db_dir / "data_load.sql"
        self.conf_file = conffile
        self.host = None
        self.shared_dir = SHARED_DIR
        self.ftp_dir = FTP_DIR
        self.jobs_dir = TEST_DIR / "temptask"
        self.vault_dir = TEST_DIR / "vault"
        self.models_dir = SHARED_DIR / "models"
        self.users_files_dir = TEST_DIR / "eco_users_files"

    def get_env(self):
        # Return the environment for postgres subprocesses
        ret = {
            "PGDATA": self.data_dir,
            "PGDATABASE": DB_NAME,
            "PGLOG": self.db_dir / "log.txt",
        }
        return ret

    def init(self):
        # Create data files
        pg_opts = [
            "-U",
            "postgres",
            "-A",
            "trust",
            "-E",
            "Latin1",
            "--locale=C",
            "--pwfile=%s" % self.pwd_file,
        ]
        cmd = [initdb_bin] + pg_opts
        SyncSubProcess(cmd, env=self.get_env())

    def launch(self):
        # Produce connection sockets in a user-writable directory (linux)
        pg_opts = [
            "-o",
            '-c unix_socket_directories="' + str(self.db_dir / "run") + '"',
        ]
        pg_opts += ["-o", '"-p %d"' % PG_PORT]
        cmd = [pgctl_bin, "start", "-W"] + pg_opts
        # Cook an environment for the subprocess
        # we do NOT use os.environ in order not to pollute current process
        # Note: the process dies right away as pgctl launches a daemon
        SyncSubProcess(
            cmd,
            env=self.get_env(),
            out_file=self.db_dir / "logs" / "postgres_start.log",
        )
        # Wait until the server port is opened
        start_time = time.time()
        while not is_port_opened(self.host, PG_PORT):
            time.sleep(0.5)
            if (time.time() - start_time) > 30:
                raise Exception("Waited too long for PG up")

    def shutdown(self, host: str):
        # Stop command
        cmd = [pgctl_bin, "stop", "-D", self.data_dir]
        # Cook an environment for the subprocess
        SyncSubProcess(
            cmd, env=self.get_env(), out_file=self.db_dir / "logs" / "postgres_stop.log"
        )
        # Wait until the server port is closed
        start_time = time.time()
        while is_port_opened(host, PG_PORT):
            time.sleep(0.5)
            if (time.time() - start_time) > 30:
                raise Exception("Waited too long for PG down")

    def runs(self) -> bool:
        if not self.host:
            return False
        return is_port_opened(self.host, PG_PORT)

    def build(self, password):
        """
        Build the DB using manage CLI option.
        """
        import cmds.manage

        cmds.manage.drop(db_name=DB_NAME, password=password)
        cmds.manage.create(db_name=DB_NAME, password=password)
        cmds.manage.build()

    def direct_SQL(self, password):
        # -h localhost force use of TCP/IP socket, otherwise psql tries local pipes in /var/run
        env = {"PGPASSWORD": password}
        pg_opts = ["-U", "postgres", "-h", self.host, "-p", "%d" % PG_PORT]
        # Data load
        schem_opts = ["-d", DB_NAME, "-f", self.data_load_file]
        cmd = [psql_bin] + pg_opts + schem_opts
        SyncSubProcess(cmd, env=env, out_file=self.db_dir / "logs" / "data_load.log")
        # TODO: Upgrade testing
        # schem_opts = ['-d', DB_NAME, '-f', self.v22_schema_creation_file]
        # cmd = [psql_bin] + pg_opts + schem_opts
        # SyncSubProcess(cmd, env=env, out_file="db_build.log")
        # # Upgrade
        # schem_opts = ['-d', DB_NAME, '-f', self.schema_upgrade_file]
        # cmd = [psql_bin] + pg_opts + schem_opts
        # SyncSubProcess(cmd, env=env, out_file="db_upgrade.log")

    def create(self):
        if not (PG_HOST and PG_PORT):
            self.host = "localhost"
            if not is_port_opened(self.host, PG_PORT):
                # Accept to reuse a server if it did not die last time
                self.init()
                self.launch()
            # TODO: Password (in call to self.direct_SQL) is ignored in this context
        else:
            self.host = PG_HOST
        self.write_config()
        self.build(DB_PASSWORD)
        self.direct_SQL(DB_PASSWORD)

    DIR_TEMPLATES = (
        Path(dirname(realpath(__file__)))
        / ".."
        / ".."
        / ".."
        / "config_templates/account_validation_mails"
    ).resolve()
    DIR_USERS_FILES = (
        Path(dirname(realpath(__file__))) / ".." / ".." / ".." / "eco_users_files"
    ).resolve()
    CAPTCHA_LIST = (
        Path(dirname(realpath(__file__))) / ".." / ".." / ".." / "utils"
    ).resolve()
    TIMETOLIVE = 10
    CONF = f"""
[default]
[conf]
DB_USER=postgres
DB_PASSWORD={DB_PASSWORD}
DB_HOST=%s
DB_PORT=%d
DB_DATABASE={DB_NAME}
RO_DB_USER=readerole
RO_DB_PASSWORD=Ec0t1x1Rd4
RO_DB_HOST=%s
RO_DB_PORT=%d
RO_DB_DATABASE={DB_NAME}
THUMBSIZELIMIT=99
SECRET_KEY = THIS KEY MUST BE CHANGED
VAULT_DIR = %s
JOBS_DIR = %s
SERVERLOADAREA = %s
FTPEXPORTAREA = %s
MODELSAREA = %s
USERSFILESAREA = %s
SECURITY_PASSWORD_HASH=sha512_crypt
SECURITY_PASSWORD_SALT=PePPER
APPMANAGER_Name=Sam One
APPMANAGER_EMAIL=someone@somewhere.org
MAILSERVICE_SECRET_KEY = THIS KEY MUST BE CHANGED ANS IS ONLY FOR TOKENS SENT BY MAIL
MAILSERVICE_SALT = "mailservice_salt"
SENDER_ACCOUNT = senderemail@testsendermailtest.com,senderpwd,senderdns
TAXOSERVER_URL = http://ecotaxoserver.dev.com
TAXOSERVER_INSTANCE_ID = 123455
TAXOSERVER_SHARED_SECRET = qsdf3fsdtre5665TY
INSTANCE_ID = EcoTaxa.01
USER_EMAIL_VERIFICATION = off
ACCOUNT_VALIDATION = off
ADD_TICKET = ***
DIR_MAIL_TEMPLATES = {DIR_TEMPLATES}
SERVERURL= http://localhost:8000
MAX_UPLOAD_SIZE = 681574400
TIMETOLIVE = {TIMETOLIVE}
"""

    def write_config(self):
        with open(str(self.conf_file), "w") as f:
            f.write(
                self.CONF
                % (
                    self.host,
                    PG_PORT,
                    self.host,
                    PG_PORT,
                    self.vault_dir,
                    self.jobs_dir,
                    self.shared_dir,
                    self.ftp_dir,
                    self.models_dir,
                    self.users_files_dir,
                )
            )

    def cleanup(self):
        # Remove data files
        if not (PG_HOST and PG_PORT):
            self.shutdown("localhost")
            shutil.rmtree(self.data_dir, ignore_errors=True)
        else:
            # Server should do the cleanup, e.g. exit docker
            pass


if __name__ == "__main__":
    HERE = Path(dirname(realpath(__file__)))
    PG_DIR = HERE / ".." / "pg_files"
    db = EcoTaxaDBFrom0(PG_DIR, Path("fakeconf"))
    try:
        db.cleanup()
    except FileNotFoundError:
        pass
    db.create()
