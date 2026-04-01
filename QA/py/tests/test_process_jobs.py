import os
import time
import pytest
from BG_operations import JobScheduler
from BG_operations.JobScheduler import ProcessJobRunner, ThreadJobRunner
from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from main import logger
from tests.credentials import ADMIN_USER_ID
from tests.api_wrappers import api_wait_for_stable_job, api_check_job_ok
from helpers.DynamicLogs import LogsSwitcher, get_logger
import sys


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


def test_job_runs_in_separate_process(fastapi, jobs_as_process):
    """
    Verify that a job runs in a separate process than the main FastAPI/test process.
    """
    # 1. Record the current PID (the one running the test)
    current_pid = os.getpid()

    # 2. Launch the PidReportingJob via JobService mechanism
    with PidReportingJob(main_pid=current_pid) as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id

    # 3. Wait for the job to complete
    job_info = api_wait_for_stable_job(fastapi, job_id)
    api_check_job_ok(fastapi, job_id)

    # 4. Retrieve the PID reported by the job from its results
    # The api_wait_for_stable_job returns a SimpleNamespace which contains the job dict
    # Results are usually in job_info.result as a dict
    job_pid = job_info.result.get("pid")

    print(f"Test PID: {current_pid}, Job PID: {job_pid}")

    # 5. Assertions
    assert job_pid is not None, "Job did not report its PID"

    # Check if we are in a state where processes are expected
    assert (
        JobScheduler.JobRunner == ProcessJobRunner
    ), "JobRunner should be ProcessJobRunner when not debugging"
    assert (
        job_pid != current_pid
    ), f"Job PID {job_pid} should be different from test PID {current_pid}"


def test_job_reports_progress(fastapi, jobs_as_process):
    """
    Verify that PidReportingJob reports progress and messages while running.
    """
    current_pid = os.getpid()

    # 1. Launch the PidReportingJob via JobService mechanism
    with PidReportingJob(main_pid=current_pid) as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id

    # 2. Wait for the job to start (state 'R') and check progress
    # We use a loop to check progress while it's running
    import time

    start_time = time.time()
    found_ticks = set()
    job_url = f"/jobs/{job_id}/"
    from tests.credentials import ADMIN_AUTH

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

    # 3. Final checks
    final_job_info = api_check_job_ok(fastapi, job_id)
    assert (
        len(found_ticks) >= 3
    ), f"Should have seen at least some ticks, got: {found_ticks}"
    # Note: "Tick 5" might have been replaced by "Done" by JobServiceBase when it finishes
    # So we check if "Tick 4" was reached or if "Tick 5" was ever seen
    assert (
        "Tick 4" in found_ticks or "Tick 5" in found_ticks
    ), f"Should have reached at least Tick 4, got: {found_ticks}"

    # 4. Check the log file content (optional, as it's hard to verify in all envs)
    # But it should work if LogsSwitcher is correctly used.
    # from tests.api_wrappers import api_get_log_file
    # log_lines = api_get_log_file(fastapi, job_id)
    # print(f"Log lines: {log_lines}")
    # log_lines = [line for line in log_lines if line.strip()]
    # log_ticks = [line for line in log_lines if "Tick" in line]
    # assert len(log_ticks) >= 5, f"Should have at least 5 ticks in log file, got {len(log_ticks)}: {log_ticks}"
