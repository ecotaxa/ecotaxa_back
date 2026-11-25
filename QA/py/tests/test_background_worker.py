# -*- coding: utf-8 -*-
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from API_operations.Prediction import PredictForProject
from API_operations.helpers.Service import Service
from BG_operations import BackgroundWorker as BackgroundWorkerMod
from BG_operations.BackgroundWorker import BackgroundWorker
from BG_operations.JobsManager import (
    BaseJobRunner,
    JobsManager,
    ProcessJobRunner,
    ThreadJobRunner,
)
from DB.Job import DBJobStateEnum, Job
from DB.helpers.Connection import DatabaseConnectionException

from tests.credentials import ADMIN_USER_ID


def _mock_scheduler_service():
    p1 = patch.object(Service, "__init__", lambda self: None)
    p2 = patch.object(Service, "__enter__", lambda self: self)
    p3 = patch.object(Service, "__exit__", lambda self, *args: None)
    p4 = patch.object(JobsManager, "fail_running_jobs", lambda self: None)
    return p1, p2, p3, p4


def test_background_worker_init_sets_filter_and_launches():
    assert issubclass(JobsManager, Service)
    with patch.object(BackgroundWorker, "launch_at_interval") as mock_launch:
        worker = BackgroundWorker()
        assert JobsManager.FILTER == [PredictForProject.JOB_TYPE]
        assert worker.the_thread is None
        mock_launch.assert_called_once_with(BackgroundWorkerMod.JOB_INTERVAL)


def test_background_worker_lifecycle():
    call_count = 0

    def mock_run_one(self):
        nonlocal call_count
        call_count += 1

    p1, p2, p3, p4 = _mock_scheduler_service()
    with (
        p1,
        p2,
        p3,
        p4,
        patch.object(JobsManager, "run_one", new=mock_run_one),
        patch.object(BackgroundWorkerMod, "JOB_INTERVAL", 0.05),
    ):
        worker = BackgroundWorker()
        try:
            assert worker.stop_event.is_set() is False
            assert worker.the_thread is not None
            assert worker.the_thread.is_alive() is True
            assert worker.the_thread.name == "BgWkThread"

            time.sleep(0.18)
            assert call_count >= 2
        finally:
            worker.shutdown()

        assert worker.stop_event.is_set() is True
        assert worker.the_thread is None


def test_background_worker_no_duplicate_threads():
    p1, p2, p3, p4 = _mock_scheduler_service()
    with (
        p1,
        p2,
        p3,
        p4,
        patch.object(JobsManager, "run_one", return_value=None),
        patch.object(BackgroundWorkerMod, "JOB_INTERVAL", 0.1),
    ):
        worker = BackgroundWorker()
        try:
            first_thread = worker.the_thread
            assert first_thread is not None
            assert first_thread.is_alive() is True

            worker.launch_at_interval(0.1)
            assert worker.the_thread is first_thread
        finally:
            worker.shutdown()

        assert worker.the_thread is None


def test_background_worker_exception_resilience():
    call_count = 0

    def flaky_run_one(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Transient scheduler failure")

    p1, p2, p3, p4 = _mock_scheduler_service()
    with (
        p1,
        p2,
        p3,
        p4,
        patch.object(JobsManager, "run_one", new=flaky_run_one),
        patch.object(BackgroundWorkerMod, "JOB_INTERVAL", 0.05),
    ):
        worker = BackgroundWorker()
        try:
            time.sleep(0.18)
            assert call_count >= 2
            assert worker.the_thread is not None
            assert worker.the_thread.is_alive() is True
        finally:
            worker.shutdown()

        assert worker.the_thread is None


def test_background_worker_shutdown_when_not_started():
    p1, p2, p3, p4 = _mock_scheduler_service()
    with p1, p2, p3, p4, patch.object(BackgroundWorker, "launch_at_interval"):
        worker = BackgroundWorker()
        worker.shutdown()
    assert worker.the_thread is None
    assert worker.stop_event.is_set() is True


def test_background_worker_calls_fail_running_jobs_on_start():
    events = []

    def mock_fail_running_jobs(self):
        events.append("fail_running_jobs")

    def mock_run_one(self):
        events.append("run_one")

    p1, p2, p3, _ = _mock_scheduler_service()
    with (
        p1,
        p2,
        p3,
        patch.object(JobsManager, "fail_running_jobs", new=mock_fail_running_jobs),
        patch.object(JobsManager, "run_one", new=mock_run_one),
        patch.object(BackgroundWorkerMod, "JOB_INTERVAL", 0.05),
    ):
        worker = BackgroundWorker()
        try:
            time.sleep(0.15)
        finally:
            worker.shutdown()

    assert events[0] == "fail_running_jobs"
    assert events.count("fail_running_jobs") == 1
    assert "run_one" in events


def test_background_worker_fail_running_jobs_exception_resilience():
    call_count = 0

    def failing_cleanup(self):
        raise RuntimeError("Startup DB error")

    def mock_run_one(self):
        nonlocal call_count
        call_count += 1

    p1, p2, p3, _ = _mock_scheduler_service()
    with (
        p1,
        p2,
        p3,
        patch.object(JobsManager, "fail_running_jobs", new=failing_cleanup),
        patch.object(JobsManager, "run_one", new=mock_run_one),
        patch.object(BackgroundWorkerMod, "JOB_INTERVAL", 0.05),
    ):
        worker = BackgroundWorker()
        try:
            time.sleep(0.15)
            assert call_count >= 1
        finally:
            worker.shutdown()


def test_process_job_runner_returns_without_tech_error_on_db_unavailable():
    runner = ProcessJobRunner.__new__(ProcessJobRunner)
    runner.db_job = SimpleNamespace(id=42)
    runner.sce_class = MagicMock()

    with (
        patch.object(
            JobsManager,
            "instantiate",
            side_effect=DatabaseConnectionException("Failed to get a DB connection"),
        ),
        patch.object(ProcessJobRunner, "tech_error") as mock_tech_error,
    ):
        runner.common_run("PID 123")

    mock_tech_error.assert_not_called()


def test_thread_job_runner_returns_without_tech_error_on_db_unavailable():
    runner = ThreadJobRunner.__new__(ThreadJobRunner)
    runner.db_job = SimpleNamespace(id=43)
    runner.sce_class = MagicMock()

    with (
        patch.object(
            JobsManager,
            "instantiate",
            side_effect=DatabaseConnectionException("Failed to get a DB connection"),
        ),
        patch.object(ThreadJobRunner, "tech_error") as mock_tech_error,
    ):
        runner.common_run("Thread 1/2")

    mock_tech_error.assert_not_called()


def test_tech_error_uses_caller_session_when_provided():
    caller_session = MagicMock()
    the_job = SimpleNamespace(state=DBJobStateEnum.Pending, progress_msg="")
    caller_session.get.return_value = the_job

    with patch("BG_operations.JobsManager.Service") as mock_service_cls:
        BaseJobRunner.tech_error(42, RuntimeError("boom"), session=caller_session)

    mock_service_cls.assert_not_called()
    caller_session.get.assert_called_once_with(Job, 42)
    assert the_job.state == DBJobStateEnum.Error
    assert the_job.progress_msg == "boom"
    caller_session.commit.assert_called_once_with()


def test_tech_error_opens_service_session_when_none_provided():
    service_session = MagicMock()
    the_job = SimpleNamespace(state=DBJobStateEnum.Pending, progress_msg="")
    service_session.get.return_value = the_job
    mock_service = MagicMock(session=service_session)
    mock_service.__enter__.return_value = mock_service
    mock_service.__exit__.return_value = None

    with patch(
        "BG_operations.JobsManager.Service", return_value=mock_service
    ) as mock_service_cls:
        BaseJobRunner.tech_error(43, RuntimeError("no session"))

    mock_service_cls.assert_called_once_with()
    service_session.get.assert_called_once_with(Job, 43)
    assert the_job.state == DBJobStateEnum.Error
    assert the_job.progress_msg == "no session"
    service_session.commit.assert_called_once_with()


def test_jobs_manager_run_one_passes_session_to_tech_error():
    mgr = JobsManager.__new__(JobsManager)
    mgr.session = MagicMock()
    pending_job = SimpleNamespace(
        id=99, owner_id=ADMIN_USER_ID, type="TestJob", params={}, state=DBJobStateEnum.Pending
    )
    mgr.session.scalars.return_value.first.return_value = pending_job

    start_err = RuntimeError("cannot spawn")
    with (
        patch.object(JobsManager, "_reap_finished_runners"),
        patch("BG_operations.JobsManager.clone_of", return_value=pending_job),
        patch("BG_operations.JobsManager.JobBO", return_value=pending_job),
        patch("BG_operations.JobsManager.JobRunner", side_effect=start_err),
        patch.object(BaseJobRunner, "tech_error") as mock_tech_error,
    ):
        mgr.run_one()

    assert pending_job.state == DBJobStateEnum.Starting
    mgr.session.commit.assert_called_once_with()
    mock_tech_error.assert_called_once_with(99, start_err, session=mgr.session)


def test_interpret_runner_result_starting_tempfail_resets_to_pending():
    from os import EX_TEMPFAIL

    session = MagicMock()
    the_job = SimpleNamespace(id=50, state=DBJobStateEnum.Starting, progress_msg="")
    session.get.return_value = the_job
    runner = SimpleNamespace(db_job=SimpleNamespace(id=50), exitcode=EX_TEMPFAIL)

    JobsManager._interpret_runner_result(runner, session)

    assert the_job.state == DBJobStateEnum.Pending
    session.commit.assert_called_once_with()


def test_interpret_runner_result_starting_failure_marks_error():
    session = MagicMock()
    the_job = SimpleNamespace(id=51, state=DBJobStateEnum.Starting, progress_msg="")
    session.get.return_value = the_job
    runner = SimpleNamespace(db_job=SimpleNamespace(id=51), exitcode=1)

    JobsManager._interpret_runner_result(runner, session)

    assert the_job.state == DBJobStateEnum.Error
    assert "exit code 1" in the_job.progress_msg
    session.commit.assert_called_once_with()
