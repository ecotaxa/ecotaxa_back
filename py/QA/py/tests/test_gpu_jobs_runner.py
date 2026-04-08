from unittest.mock import MagicMock

import pytest

import gpu_jobs_runner
from BG_operations.JobScheduler import JobScheduler


@pytest.fixture
def common_mocks(monkeypatch):
    mock_gpu_predict = MagicMock()
    mock_gpu_predict.JOB_TYPE = "Prediction"
    monkeypatch.setattr("gpu_jobs_runner.GPUPredictForProject", mock_gpu_predict)

    mock_scheduler_cls = MagicMock(spec=JobScheduler)
    monkeypatch.setattr("gpu_jobs_runner.JobScheduler", mock_scheduler_cls)

    mock_scheduler_instance = mock_scheduler_cls.return_value.__enter__.return_value

    mock_print = MagicMock()
    monkeypatch.setattr("builtins.print", mock_print)

    mock_sleep = MagicMock()
    monkeypatch.setattr("gpu_jobs_runner.time.sleep", mock_sleep)

    return {
        "gpu_predict": mock_gpu_predict,
        "scheduler_cls": mock_scheduler_cls,
        "scheduler_instance": mock_scheduler_instance,
        "print": mock_print,
        "sleep": mock_sleep,
    }


def test_main_one_shot_with_job(monkeypatch, common_mocks):
    # Setup environment
    monkeypatch.setenv("ONE_SHOT", "1")

    mock_scheduler_cls = common_mocks["scheduler_cls"]
    mock_scheduler_instance = common_mocks["scheduler_instance"]
    mock_gpu_predict = common_mocks["gpu_predict"]

    # Simulate that a job was run (the_runner is set)
    def side_effect_run_one():
        mock_scheduler_cls.the_runner = MagicMock()

    mock_scheduler_instance._run_one.side_effect = side_effect_run_one
    mock_scheduler_cls.the_runner = None

    # Execute
    gpu_jobs_runner.main()

    # Verify
    mock_scheduler_instance._run_one.assert_called_once()
    assert mock_scheduler_cls.INCLUDE == [mock_gpu_predict.JOB_TYPE]


def test_main_one_shot_no_job(monkeypatch, common_mocks):
    # Setup environment
    monkeypatch.setenv("ONE_SHOT", "1")

    mock_scheduler_cls = common_mocks["scheduler_cls"]
    mock_scheduler_instance = common_mocks["scheduler_instance"]
    mock_print = common_mocks["print"]

    mock_scheduler_cls.the_runner = None

    # Execute
    gpu_jobs_runner.main()

    # Verify
    mock_scheduler_instance._run_one.assert_called_once()
    mock_print.assert_called_with("WARNING: Nothing to do in one shot mode")


def test_main_loop_until_job(monkeypatch, common_mocks):
    # Setup environment
    monkeypatch.delenv("ONE_SHOT", raising=False)

    mock_scheduler_cls = common_mocks["scheduler_cls"]
    mock_scheduler_instance = common_mocks["scheduler_instance"]
    mock_sleep = common_mocks["sleep"]

    # Simulate no job for 2 iterations, then a job
    mock_scheduler_cls.the_runner = None

    def side_effect_run_one():
        if mock_scheduler_instance._run_one.call_count >= 3:
            mock_scheduler_cls.the_runner = MagicMock()

    mock_scheduler_instance._run_one.side_effect = side_effect_run_one

    # Execute
    gpu_jobs_runner.main()

    # Verify
    assert mock_scheduler_instance._run_one.call_count == 3
    assert mock_sleep.call_count == 3
    mock_sleep.assert_called_with(10)
