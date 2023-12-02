import os
import shutil
import time
from multiprocessing import Process
from random import random

import pytest
from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from BG_operations.JobScheduler import JobScheduler
from helpers.DynamicLogs import get_logger, LogsSwitcher, logger_nullify_after_fork

from tests.credentials import ADMIN_USER_ID
from tests.jobs import api_wait_for_stable_job

logger = get_logger(__name__)


# Create a fake job to run
class FakeRandomJob(JobServiceBase):
    JOB_TYPE = "FakeRandom"

    def run(self, current_user_id: int) -> None:
        # Just create pending job
        self.create_job(self.JOB_TYPE, current_user_id)

    def init_args(self, args: ArgsDict) -> ArgsDict:
        return args

    def do_background(self) -> None:
        with LogsSwitcher(self):
            logger.info("%d Starting" % self.job_id)
            dur = random() / 1000
            time.sleep(dur)
            logger.info("%d Done" % self.job_id)
            logger.info("pid %d session %s", os.getpid(), self.session)
            self.set_job_result(errors=[], infos={"wait": dur})


def launchSchedulerSubProcess():
    # Release DB-related resources, which cannot be shared with other process
    from API_operations.helpers.Service import Service

    Service.re_init_after_fork()
    logger_nullify_after_fork()
    JobScheduler.launch_at_interval(0.01)
    while True:
        time.sleep(10)
    # time.sleep(30)
    # JobScheduler.shutdown()
    # assert JobScheduler.is_sane_on_shutdown()


# It's quite long to run so comment out or remove below line to execute
@pytest.mark.skip
def test_log_file_exists_if_job_exists(fastapi):
    # Hammer job execution subsystem until a race condition eventually appears
    # What was randomly seen is the message in https://github.com/ecotaxa/ecotaxa_front/issues/688:
    #     File "/usr/lib/python3.8/threading.py", line 890, in _bootstrap self._bootstrap_inner()
    #     File "/usr/lib/python3.8/threading.py", line 932, in _bootstrap_inner self.run()
    #     File "/app/BG_operations/JobScheduler.py", line 40, in run sce.run_in_background()
    #     File "/app/API_operations/helpers/JobService.py", line 72, in run_in_background self.do_background()
    #     File "/app/API_operations/imports/Import.py", line 71, in do_background with LogsSwitcher(self):
    #     File "/app/helpers/DynamicLogs.py", line 81, in enter self.switch()
    #     File "/app/helpers/DynamicLogs.py", line 85, in switch switch_to = self.emitter.log_file_path()
    #     File "/app/API_operations/helpers/JobService.py", line 59, in log_file_path log_file = self.temp_for_jobs.base_dir_for(self.job_id) / self.JOB_LOG_FILE_NAME
    #     File "/app/FS/TempDirForTasks.py", line 27, in base_dir_for ret.mkdir()
    #     File "/usr/lib/python3.8/pathlib.py", line 1266, in mkdir self._accessor.mkdir(self, mode)
    #     FileExistsError: [Errno 17] File exists: '/ecotaxa_master/temptask/task044333'
    # And more funny, a message in the log file indicating it cannot create the log file.
    #     File "/usr/lib/python3.8/threading.py", line 890, in _bootstrap self._bootstrap_inner()
    #     File "/usr/lib/python3.8/threading.py", line 932, in _bootstrap_inner self.run()
    #     File "/app/BG_operations/JobScheduler.py", line 39, in run sce.run_in_background()
    #     File "/app/API_operations/helpers/JobService.py", line 76, in run_in_background self.do_background()
    #     File "/app/API_operations/admin/NightlyJob.py", line 54, in do_background with LogsSwitcher(self):
    #     File "/app/helpers/DynamicLogs.py", line 85, in __enter__ self.switch()
    #     File "/app/helpers/DynamicLogs.py", line 93, in switch _the_handler.switch_to(switch_to)
    #     File "/app/helpers/DynamicLogs.py", line 38, in switch_to alt_handler = logging.FileHandler(new_filename_or_stream)
    #     File "/usr/lib/python3.8/logging/__init__.py", line 1143, in __init__ StreamHandler.__init__(self, self._open())
    #     File "/usr/lib/python3.8/logging/__init__.py", line 1172, in _open return open(self.baseFilename, self.mode, encoding=self.encoding)
    #     FileNotFoundError: [Errno 2] No such file or directory: '/home/ecotaxa/ecotaxa/temptask/task089024/TaskLogBack.txt'
    # Note: both problems occur in the job runner thread.

    # Shutdown the default scheduler which is too slow and single
    JobScheduler.shutdown()
    JobScheduler.do_run.wait()
    assert JobScheduler.the_runner is None
    assert JobScheduler.the_timer is None
    # Cleanup any previous run
    for jt in database.jobs_dir.glob("task*"):
        shutil.rmtree(jt)

    sub_processes = []
    # We have 100 cnx in the test DB
    # 34 read-only connections
    # 35 read-write connections after fresh startup
    # psql -p 5440 -h /home/laurent/Devs/from_Lab/ecotaxa_back/QA/py/pg_files/run -U postgres
    # postgres=# select query, pid as process_id,
    #        usename as username,
    #        datname as database_name,
    #        client_addr as client_address,
    #        application_name,
    #        backend_start,
    #        state,
    #        state_change
    # from pg_stat_activity;
    for sched in range(45):
        p = Process(target=launchSchedulerSubProcess)
        p.start()
        sub_processes.append(p)
    nb_jobs = 12000
    for i in range(nb_jobs):
        time.sleep(random() / 100)
        # time.sleep(random() * 5)
        with FakeRandomJob() as job:
            job.run(ADMIN_USER_ID)
        job_dict = api_wait_for_stable_job(fastapi, job.job_id, 40)
        assert job_dict["state"] == "F", "Failed for %s" % job_dict
        logger.info("Done for %d", job_dict["id"])
    for p in sub_processes:
        p.kill()
        p.join()
