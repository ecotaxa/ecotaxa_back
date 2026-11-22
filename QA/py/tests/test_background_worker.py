# -*- coding: utf-8 -*-
import time
from unittest.mock import patch

from API_operations.Prediction import PredictForProject
from API_operations.helpers.Service import Service
from BG_operations import BackgroundWorker as BackgroundWorkerMod
from BG_operations.BackgroundWorker import BackgroundWorker
from BG_operations.JobsManager import JobsManager


def _mock_scheduler_service():
    p1 = patch.object(JobsManager, "__init__", lambda self: None)
    p2 = patch.object(JobsManager, "__enter__", lambda self: self)
    p3 = patch.object(JobsManager, "__exit__", lambda self, *args: None)
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
    with patch.object(BackgroundWorker, "launch_at_interval"):
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
