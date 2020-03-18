#
# Manage processes during tests
#
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from os.path import join, abspath, dirname
from pathlib import Path

cur_file = __file__
cur_file_dir = dirname(cur_file)

pg_lib = "/usr/lib/postgresql/10/bin/"
ecotaxa_src_dir = abspath(join(cur_file, "..", "..", ".."))
db_dir = abspath(join(ecotaxa_src_dir, "..", "DB"))

# the path to some python we need
pgctl_bin = join(pg_lib, "pg_ctl")
runserver_py = join(ecotaxa_src_dir, "runserver.py")
manage_py = join(ecotaxa_src_dir, "manage.py")
coverage_bin = "coverage"
# check dependencies before doing anything
mustExist = [runserver_py, manage_py]  # , pgctl_bin, db_dir]
for aFile in mustExist:
    if not Path(aFile).exists():
        print("File/directory %s not found where expected" % aFile)
        sys.exit(-1)

ecotaxa_src_root = join("..", "..")



class Captured(object):
    """
    Utility class to capture output
    """

    def __init__(self):
        self.file = sys.stdout

    def fileno(self):
        return self.file.fileno()

    def write(self, str_):
        print("CAP: ", str_)


class BackgroundSubProcess(object):
    """
        A process launched in background.
    """

    def __init__(self, args, cwd=None):
        self.pid = subprocess.Popen(args=args, shell=False, cwd=cwd,
                                    universal_newlines=True, stderr=subprocess.STDOUT)

    def stop(self):
        # SIGINT is equivalent to keyboard ctrl-c and is correctly managed by most programs
        self.pid.send_signal(signal.SIGINT)
        self.pid.wait(10)


class TstProcesses(object):
    """
        A class for ensuring that the processes needed for tests are running and did not crash.
    """
    pg_sub_process_wanted = False

    def __init__(self):
        # noinspection PyTypeChecker
        self.pg_sub_process: SyncSubProcess = None
        # noinspection PyTypeChecker
        self.flask_sub_process: BackgroundSubProcess = None
        # noinspection PyTypeChecker
        self.db_create_process: SyncSubProcess = None

    # The environment for postgres subprocesses
    pg_env = {"PGDATA": join(db_dir, "Data"),
              "PGDATABASE": "ecotaxa",
              "PGLOG": join(db_dir + "log.txt")
              }

    def _launch_postgres(self):
        # Produce connection sockets in a user-writable directory (linux)
        pg_opts = ['-o', '-c unix_socket_directories="' + join(db_dir, "run") + '"']
        cmd = [pgctl_bin, "start", "-W"] + pg_opts
        # Cook an environment for the subprocess
        # we do NOT use os.environ in order not to pollute current process
        # Note: the process dies right away as pgctl launches a daemon
        self.pg_sub_process = SyncSubProcess(cmd, env=self.pg_env)

    def _create_db(self):
        # Use current python
        cmd = [sys.executable]
        cmd += [manage_py, "CreateDB", "-U", "-Y"]
        self.db_create_process = SyncSubProcess(cmd, cwd=ecotaxa_src_dir)

    def _stop_postgres(self):
        cmd = [pgctl_bin, "stop", "-W"]
        # Do a clean shutdown of the DB
        SyncSubProcess(cmd, env=self.pg_env)
        # TODO really picky: Wait until the server is gone

    @staticmethod
    def wait_until_opened_port(host: str, port: int, max_time: int = 10):
        start_time = time.time()
        while True:
            try:
                socket.gethostbyname(host)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((host, port))
                s.close()
                return
            except socket.error as exc:
                time.sleep(0.1)

    def _launch_webserver(self):
        # Use current python
        cmd = [sys.executable]
        # Add coverage instrumentation
        cmd += ["-m", "coverage", "run",
                "--include=" + TstProcesses.prj_dir]
        # Launch runserver from flask, it's a bundled command
        # Don't let the server self-reload otherwise coverage gets lost
        cmd += [manage_py, "runserver", "-R"]
        self.flask_sub_process = BackgroundSubProcess(cmd, cwd=ecotaxa_src_dir)
        # Wait until the server opens the port
        self.wait_until_opened_port("0.0.0.0", 5000)

    # Only examine coverage for current project
    prj_dir = os.path.join(os.path.dirname(cur_file_dir), "*")

    @staticmethod
    def generate_coverage():
        # Use current python
        cmd = [sys.executable, "-m", "coverage", "html"]
        # Remove any stale output
        shutil.rmtree("htmlcov", ignore_errors=True)
        # Generate a new one
        SyncSubProcess(cmd, None)

    def _stop_webserver(self):
        if self.flask_sub_process is not None:
            self.flask_sub_process.stop()
        # Wait for clean termination, otherwise coverage tool finds little to analyze
        # time.sleep(5)

    def is_up_and_running(self, do_create_db=True, do_launch_server=True):
        """
            Entry point from tests.
        """
        # if self.pg_sub_process is None and self.pg_sub_process_wanted:
        #     self._launch_postgres()
        if do_create_db:
            self._create_db()
        if do_launch_server:
            if self.flask_sub_process is None:
                self._launch_webserver()
        return not do_launch_server or self.flask_sub_process is not None

    def shutdown(self):
        """
            Entry point from tests teardown.
        """
        self._stop_webserver()
        if self.pg_sub_process_wanted:
            self._stop_postgres()
