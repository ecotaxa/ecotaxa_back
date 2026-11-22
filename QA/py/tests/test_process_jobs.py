import os
import re
import time
from unittest.mock import patch

import pytest

from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from BG_operations import JobsManager as JobsManagerMod
from BG_operations.JobsManager import ProcessJobRunner
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
    Switch JobsManager to ProcessJobRunner for the duration of the test.
    """
    old_runner = JobsManagerMod.JobRunner
    JobsManagerMod.JobRunner = ProcessJobRunner
    yield
    JobsManagerMod.JobRunner = old_runner


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
        JobsManagerMod.JobRunner == ProcessJobRunner
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
                if any(
                    re.search(r"Running job \d+ in PID \d+", line) for line in log_lines
                ):
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


def test_job_delete_pending(fastapi, no_scheduler, jobs_as_process):
    """
    Verify that a pending job can be deleted and it goes to Error state with Killed message.
    """
    # 1. Launch a job but kill it faster than the Scheduler picks it
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

    # 5. Verify the log file contains the "Process killed by" line
    log_lines = api_get_log_file(fastapi, job_id)
    print(f"Log lines after kill: {log_lines}")
    assert any(
        "Process killed by" in line for line in log_lines
    ), f"Log file should contain kill message, got: {log_lines}"


class HardExitJob(JobServiceBase):
    JOB_TYPE = "HardExit"
    logger = get_logger(__name__)

    def __init__(self, exit_code: int = 42):
        super().__init__()
        self.exit_code = exit_code

    def init_args(self, args: ArgsDict) -> ArgsDict:
        super().init_args(args)
        args["exit_code"] = self.exit_code
        return args

    def run(self, current_user_id: int) -> None:
        self.create_job(self.JOB_TYPE, current_user_id)

    def do_background(self) -> None:
        # Exit directly without setting job result or calling update_progress
        os._exit(self.exit_code)


def test_job_hard_exit_reconciled(fastapi, jobs_as_process):
    """
    Verify that when a process exits abruptly (e.g. crash/os._exit),
    JobsManager interprets the exitcode and reconciles the DB job state to Error.
    """
    with HardExitJob(exit_code=42) as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id

    job_info = api_wait_for_stable_job(fastapi, job_id)
    assert job_info.state == "E"
    assert "exit code 42" in job_info.progress_msg


class ParallelSleepJob(JobServiceBase):
    JOB_TYPE = "ParallelSleep"
    logger = get_logger(__name__)

    def __init__(self, duration: float = 1.0):
        super().__init__()
        self.duration = duration

    def init_args(self, args: ArgsDict) -> ArgsDict:
        super().init_args(args)
        args["duration"] = self.duration
        return args

    def run(self, current_user_id: int) -> None:
        self.create_job(self.JOB_TYPE, current_user_id)

    def do_background(self) -> None:
        start = time.monotonic()
        time.sleep(self.duration)
        end = time.monotonic()
        self.set_job_result(
            errors=[], infos={"start": start, "end": end, "pid": os.getpid()}
        )


def test_parallel_jobs_execution(fastapi, jobs_as_process):
    """
    Verify that JobsManager runs multiple jobs in parallel and defines MAX_PARALLEL_JOBS.
    """
    assert JobsManagerMod.MAX_PARALLEL_JOBS == 8

    job_ids = []
    t0 = time.monotonic()
    for _ in range(4):
        with ParallelSleepJob(duration=1.0) as job:
            job.run(ADMIN_USER_ID)
            job_ids.append(job.job_id)

    results = []
    for job_id in job_ids:
        job_info = api_wait_for_stable_job(fastapi, job_id)
        api_check_job_ok(fastapi, job_id)
        results.append(job_info.result)

    elapsed = time.monotonic() - t0
    assert elapsed < 3.5, f"4 x 1s jobs took {elapsed:.2f}s, expected parallel execution"
    pids = {r["pid"] for r in results}
    assert len(pids) == 4, f"Expected 4 distinct job PIDs, got {pids}"
    # All 4 jobs should have overlapped in time
    max_start = max(r["start"] for r in results)
    min_end = min(r["end"] for r in results)
    assert max_start < min_end, f"Jobs did not overlap in time: {results}"


def test_parallel_jobs_limit_respected(fastapi, no_scheduler, jobs_as_process):
    """
    Verify that JobsManager never runs more than MAX_PARALLEL_JOBS concurrently.
    """
    job_ids = []
    for _ in range(4):
        with ParallelSleepJob(duration=0.6) as job:
            job.run(ADMIN_USER_ID)
            job_ids.append(job.job_id)

    with patch.object(JobsManagerMod, "MAX_PARALLEL_JOBS", 2):
        with JobsManagerMod.JobsManager() as mgr:
            mgr.run_one()
        assert len(JobsManagerMod.JobsManager.the_runners) == 2

        deadline = time.monotonic() + 15
        while JobsManagerMod.JobsManager.the_runners and time.monotonic() < deadline:
            time.sleep(0.1)
            with JobsManagerMod.JobsManager() as mgr:
                mgr.run_one()
            assert len(JobsManagerMod.JobsManager.the_runners) <= 2

        assert len(JobsManagerMod.JobsManager.the_runners) == 0

    for job_id in job_ids:
        job_info = api_wait_for_stable_job(fastapi, job_id, max_wait=5)
        assert job_info.state == "F"


def test_wait_runners_reaps_finished_before_head_finishes(
    fastapi, no_scheduler, jobs_as_process
):
    """
    Verify that wait_runners() reaps and reconciles a fast-exiting runner
    without waiting for an earlier long-running runner (no head-of-line blocking).
    """
    import threading

    with ParallelSleepJob(duration=2.5) as slow_job:
        slow_job.run(ADMIN_USER_ID)
        slow_id = slow_job.job_id

    with JobsManagerMod.JobsManager() as mgr:
        mgr.run_one()

    # Wait for the slow job process to actually start and reach Running ('R')
    # before launching the fast-crashing job, so it isn't still in Pending ('P')
    # on slower CI runners when the fast job finishes.
    start_deadline = time.monotonic() + 5.0
    slow_state = None
    while time.monotonic() < start_deadline:
        rsp_slow = fastapi.get(
            JOB_QUERY_URL.format(job_id=slow_id), headers=ADMIN_AUTH
        )
        slow_state = rsp_slow.json()["state"]
        if slow_state == "R":
            break
        time.sleep(0.05)
    assert slow_state == "R", f"Slow job did not enter Running state, got {slow_state}"

    with HardExitJob(exit_code=42) as fast_crash_job:
        fast_crash_job.run(ADMIN_USER_ID)
        fast_id = fast_crash_job.job_id

    with JobsManagerMod.JobsManager() as mgr:
        mgr.run_one()

    assert len(JobsManagerMod.JobsManager.the_runners) == 2
    # Ensure the slow job is first in the_runners (head-of-line)
    assert JobsManagerMod.JobsManager.the_runners[0].db_job.id == slow_id

    wait_thread = threading.Thread(target=JobsManagerMod.JobsManager.wait_runners)
    wait_thread.start()

    try:
        # Fast crashing job should be reaped and reconciled to Error well before the 2.5s slow job finishes
        deadline = time.monotonic() + 2.0
        fast_state = None
        while time.monotonic() < deadline:
            rsp = fastapi.get(JOB_QUERY_URL.format(job_id=fast_id), headers=ADMIN_AUTH)
            fast_state = rsp.json()["state"]
            if fast_state == "E":
                break
            time.sleep(0.05)

        assert fast_state == "E", "Fast crashing runner was blocked behind slow runner"
        # Slow job should still be running at this point
        rsp_slow = fastapi.get(
            JOB_QUERY_URL.format(job_id=slow_id), headers=ADMIN_AUTH
        )
        assert rsp_slow.json()["state"] == "R"
    finally:
        wait_thread.join(timeout=10)

    assert not wait_thread.is_alive()
    assert len(JobsManagerMod.JobsManager.the_runners) == 0
    slow_info = api_wait_for_stable_job(fastapi, slow_id, max_wait=5)
    assert slow_info.state == "F"


def test_wait_runners_with_thread_runners(fastapi, no_scheduler):
    """
    Verify that wait_runners() handles ThreadJobRunner instances cleanly.
    """
    old_runner = JobsManagerMod.JobRunner
    JobsManagerMod.JobRunner = JobsManagerMod.ThreadJobRunner
    try:
        job_ids = []
        for dur in (0.3, 0.05):
            with ParallelSleepJob(duration=dur) as job:
                job.run(ADMIN_USER_ID)
                job_ids.append(job.job_id)

        with JobsManagerMod.JobsManager() as mgr:
            mgr.run_one()

        assert len(JobsManagerMod.JobsManager.the_runners) == 2
        JobsManagerMod.JobsManager.wait_runners()
        assert len(JobsManagerMod.JobsManager.the_runners) == 0

        for job_id in job_ids:
            job_info = api_wait_for_stable_job(fastapi, job_id, max_wait=5)
            assert job_info.state == "F"
    finally:
        JobsManagerMod.JobRunner = old_runner


def test_fail_running_jobs(fastapi, no_scheduler):
    """
    Verify that JobsManager.fail_running_jobs() sets positive-ID Running jobs
    (respecting FILTER) to Error, leaving negative-ID, Pending, Finished,
    and filtered jobs untouched, and that BackgroundWorker triggers it on start.
    """
    from API_operations.Prediction import PredictForProject
    from API_operations.helpers.Service import Service
    from BG_operations.BackgroundWorker import BackgroundWorker
    from BO.Job import JobBO
    from DB.Job import Job, DBJobStateEnum

    created_ids = []
    try:
        with Service() as svc:
            j_running = JobBO.create_job(ADMIN_USER_ID, ParallelSleepJob.JOB_TYPE, {})
            j_running.state = DBJobStateEnum.Running
            svc.session.add(j_running)

            j_archived = JobBO.create_job(ADMIN_USER_ID, ParallelSleepJob.JOB_TYPE, {})
            j_archived.state = DBJobStateEnum.Running
            svc.session.add(j_archived)

            j_pending = JobBO.create_job(ADMIN_USER_ID, ParallelSleepJob.JOB_TYPE, {})
            j_pending.state = DBJobStateEnum.Pending
            svc.session.add(j_pending)

            j_finished = JobBO.create_job(ADMIN_USER_ID, ParallelSleepJob.JOB_TYPE, {})
            j_finished.state = DBJobStateEnum.Finished
            svc.session.add(j_finished)

            j_filtered = JobBO.create_job(ADMIN_USER_ID, PredictForProject.JOB_TYPE, {})
            j_filtered.state = DBJobStateEnum.Running
            svc.session.add(j_filtered)

            svc.session.flush()
            # Negate ID to simulate an archived Running job
            j_archived.id = -j_archived.id
            running_id = j_running.id
            archived_id = j_archived.id
            pending_id = j_pending.id
            finished_id = j_finished.id
            filtered_id = j_filtered.id
            created_ids = [running_id, archived_id, pending_id, finished_id, filtered_id]
            svc.session.commit()

        with JobsManagerMod.JobsManager() as mgr:
            old_filter = JobsManagerMod.JobsManager.FILTER
            JobsManagerMod.JobsManager.FILTER = [PredictForProject.JOB_TYPE]
            try:
                mgr.fail_running_jobs()
            finally:
                JobsManagerMod.JobsManager.FILTER = old_filter

        with Service() as svc:
            assert svc.session.get(Job, running_id).state == DBJobStateEnum.Error
            assert svc.session.get(Job, archived_id).state == DBJobStateEnum.Running
            assert svc.session.get(Job, pending_id).state == DBJobStateEnum.Pending
            assert svc.session.get(Job, finished_id).state == DBJobStateEnum.Finished
            assert svc.session.get(Job, filtered_id).state == DBJobStateEnum.Running

            # Reset running_id to Running and delete pending_id so BackgroundWorker doesn't run it
            svc.session.get(Job, running_id).state = DBJobStateEnum.Running
            svc.session.delete(svc.session.get(Job, pending_id))
            svc.session.commit()

        # BackgroundWorker sets FILTER=[PredictForProject.JOB_TYPE] and runs fail_running_jobs() on start
        worker = BackgroundWorker()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with Service() as svc:
                    job_row = svc.session.get(Job, running_id)
                    if job_row is not None and job_row.state == DBJobStateEnum.Error:
                        break
                time.sleep(0.05)
        finally:
            worker.shutdown()

        with Service() as svc:
            assert svc.session.get(Job, running_id).state == DBJobStateEnum.Error
            assert svc.session.get(Job, archived_id).state == DBJobStateEnum.Running
            assert svc.session.get(Job, finished_id).state == DBJobStateEnum.Finished
            assert svc.session.get(Job, filtered_id).state == DBJobStateEnum.Running
    finally:
        if created_ids:
            with Service() as svc:
                for jid in created_ids:
                    row = svc.session.get(Job, jid)
                    if row is not None:
                        svc.session.delete(row)
                svc.session.commit()
