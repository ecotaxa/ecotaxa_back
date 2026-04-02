import os
import time

import pytest

from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from BG_operations import JobScheduler
from BG_operations.JobScheduler import ProcessJobRunner
from helpers.DynamicLogs import LogsSwitcher, get_logger
from tests.api_wrappers import (
    api_wait_for_stable_job,
    api_check_job_ok,
    api_get_log_file,
    JOB_QUERY_URL,
    JOB_DELETE_URL,
)
from tests.export_shared import JOB_LOG_DOWNLOAD_URL
from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH


@pytest.fixture
def jobs_as_process():
    """
    Switch JobScheduler to ProcessJobRunner for the duration of the test.
    """
    old_runner = JobScheduler.JobRunner
    JobScheduler.JobRunner = ProcessJobRunner
    yield
    JobScheduler.JobRunner = old_runner


# Define a job that reports its PID in the result
class PidReportingJob(JobServiceBase):
    JOB_TYPE = "PidReporting"
    logger = get_logger(__name__)

    def __init__(self, main_pid: int = None):
        super().__init__()
        self.main_pid = main_pid

    def init_args(self, args: ArgsDict) -> ArgsDict:
        super().init_args(args)
        args["main_pid"] = self.main_pid
        return args

    def run(self, current_user_id: int) -> None:
        """
        Initial creation, do security and consistency checks, then create the job.
        """
        # Security OK, create pending job
        self.create_job(self.JOB_TYPE, current_user_id)

    def do_background(self) -> None:
        self.check_pid()
        # Report the PID and some other info to confirm it's running
        with LogsSwitcher(self):
            for i in range(8):
                time.sleep(0.5)
                self.logger.info(f"Tick {i+1}")
                self.update_progress(20 * (i + 1), f"Tick {i+1}")
        self.set_job_result(errors=[], infos={"pid": os.getpid()})

    def check_pid(self):
        # Check if current pid is same as main_pid
        current_pid = os.getpid()
        if self.main_pid and current_pid == self.main_pid:
            raise ValueError(
                f"Job running in same process as main one (PID: {self.main_pid}, Current: {current_pid})"
            )


def test_job_process_behavior(fastapi, jobs_as_process):
    """
    Verify that a job runs in a separate process than the main FastAPI/test process,
    and that it reports progress and messages while running.
    """
    current_pid = os.getpid()

    # 1. Launch the PidReportingJob via JobService mechanism
    with PidReportingJob(main_pid=current_pid) as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id

    # 2. Wait for the job to start (state 'R') and check progress
    # We use a loop to check progress while it's running
    start_time = time.time()
    found_ticks = set()
    job_url = JOB_QUERY_URL.format(job_id=job_id)

    while time.time() - start_time < 10:  # 10s timeout
        rsp = fastapi.get(job_url, headers=ADMIN_AUTH)
        job_info = rsp.json()
        if job_info["progress_msg"] and "Tick" in job_info["progress_msg"]:
            found_ticks.add(job_info["progress_msg"])
            print(
                f"Current progress: {job_info['progress_pct']}% - {job_info['progress_msg']}"
            )

        if job_info["state"] == "F":
            break
        time.sleep(0.5)

    # 3. Final checks and PID verification
    job_info_obj = api_wait_for_stable_job(fastapi, job_id)
    api_check_job_ok(fastapi, job_id)

    # Check if we are in a state where processes are expected
    assert (
        JobScheduler.JobRunner == ProcessJobRunner
    ), "JobRunner should be ProcessJobRunner when not debugging"

    # Retrieve the PID reported by the job from its results
    job_pid = job_info_obj.result.get("pid")
    print(f"Test PID: {current_pid}, Job PID: {job_pid}")
    assert job_pid is not None, "Job did not report its PID"
    assert (
        job_pid != current_pid
    ), f"Job PID {job_pid} should be different from test PID {current_pid}"

    # Verify progress messages
    assert (
        len(found_ticks) >= 3
    ), f"Should have seen at least some ticks, got: {found_ticks}"
    # Note: "Tick 5" might have been replaced by "Done" by JobServiceBase when it finishes
    # So we check if "Tick 4" was reached or if "Tick 5" was ever seen
    assert (
        "Tick 4" in found_ticks or "Tick 5" in found_ticks
    ), f"Should have reached at least Tick 4, got: {found_ticks}"

    # 4. Check the log file content
    log_lines = api_get_log_file(fastapi, job_id)
    print(f"Log lines: {log_lines}")
    log_lines = [line for line in log_lines if line.strip()]
    log_ticks = [line for line in log_lines if "Tick" in line]
    assert (
        len(log_ticks) == 8
    ), f"Should have exactly 8 ticks in log file, got {len(log_ticks)}: {log_ticks}"
    for i in range(1, 9):
        assert any(
            f"Tick {i}" in line for line in log_ticks
        ), f"Tick {i} missing from log file"


def test_job_kill(fastapi, jobs_as_process):
    """
    Verify that a job can be killed (deleted) while running.
    """
    current_pid = os.getpid()

    # 1. Launch the PidReportingJob
    # It runs for 8 * 0.5s = 4s total.
    with PidReportingJob(main_pid=current_pid) as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id

    # 2. Wait for it to start running
    job_get_url = JOB_QUERY_URL.format(job_id=job_id)
    job_delete_url = JOB_DELETE_URL.format(job_id=job_id)
    start_time = time.time()
    while time.time() - start_time < 5:
        rsp = fastapi.get(job_get_url, headers=ADMIN_AUTH)
        job_info = rsp.json()
        if job_info["state"] == "R":
            # Check if PID is already in the log file (required for kill_process)
            try:
                log_lines = api_get_log_file(fastapi, job_id)
                if any("Running in PID" in line for line in log_lines):
                    break
            except Exception:
                pass
        time.sleep(0.1)
    else:
        pytest.fail("Job did not start running or didn't write PID in time")

    # 3. Kill it after ~2 seconds of total run (we already waited some time for it to start)
    # The job ticks every 0.5s.
    time.sleep(1.0)

    # 4. Delete the job (which should kill it)
    rsp = fastapi.delete(job_delete_url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200

    # 5. Check if it's really killed and state is Error/Killed
    start_time = time.time()
    while time.time() - start_time < 5:
        rsp = fastapi.get(job_get_url, headers=ADMIN_AUTH)
        job_info = rsp.json()
        if job_info["state"] == "E" and job_info["progress_msg"] == "Killed":
            break
        time.sleep(0.1)
    else:
        pytest.fail(
            f"Job was not killed properly or didn't reach Error state. Current: {job_info}"
        )

    # Wait for the process to truly exit
    time.sleep(1.0)

    # 5. Verify it's in Error state with Killed message
    # Wait a bit for the state to update if it's not immediate
    # Actually JobCRUDService.delete updates the state immediately in DB
    rsp = fastapi.get(job_get_url, headers=ADMIN_AUTH)
    job_info = rsp.json()
    assert (
        job_info["state"] == "E"
    ), f"Job state should be 'E' (Error) after kill, got: {job_info['state']}"
    assert (
        job_info["progress_msg"] == "Killed"
    ), f"Job progress_msg should be 'Killed' after kill, got: {job_info['progress_msg']}"

    # 6. Verify a NEW job can be submitted and run after the previous one was killed
    with PidReportingJob(main_pid=current_pid) as job2:
        job2.run(ADMIN_USER_ID)
        job2_id = job2.job_id

    # Wait for the second job to finish successfully
    api_wait_for_stable_job(fastapi, job2_id)
    api_check_job_ok(fastapi, job2_id)


def test_job_delete_pending(fastapi, jobs_as_process):
    """
    Verify that a pending job can be deleted and it goes to Error state with Killed message.
    """
    # 1. Launch a job but kill it faster than the Scheduler
    current_pid = os.getpid()
    with PidReportingJob(main_pid=current_pid) as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id

    # 2. Verify it's pending
    job_get_url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(job_get_url, headers=ADMIN_AUTH)
    assert rsp.json()["state"] == "P"

    # 3. Delete it
    job_delete_url = JOB_DELETE_URL.format(job_id=job_id)
    rsp = fastapi.delete(job_delete_url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200

    # 4. Verify it's in Error state with Killed message
    rsp = fastapi.get(job_get_url, headers=ADMIN_AUTH)
    job_info = rsp.json()
    assert job_info["state"] == "E"
    assert job_info["progress_msg"] == "Killed"

    # 6. Verify the log file contains the "Process killed by" line
    log_lines = api_get_log_file(fastapi, job_id)
    print(f"Log lines after kill: {log_lines}")
    assert any(
        "Process killed by" in line for line in log_lines
    ), f"Log file should contain kill message, got: {log_lines}"
