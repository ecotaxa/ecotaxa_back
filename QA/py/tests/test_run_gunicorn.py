# -*- coding: utf-8 -*-
import sys
from unittest.mock import MagicMock, patch

from gunicorn.app.base import BaseApplication

from BG_operations.BackgroundWorker import BackgroundWorker
import run as run_mod


def _simulate_master_lifecycle(app):
    server = MagicMock()
    app.cfg.when_ready(server)
    app.cfg.on_exit(server)


def test_run_gunicorn_starts_background_worker_when_enabled():
    mock_worker = MagicMock(spec=BackgroundWorker)
    with (
        patch.dict(sys.modules, {"main": MagicMock(app=MagicMock())}),
        patch(
            "BG_operations.BackgroundWorker.BackgroundWorker",
            return_value=mock_worker,
        ) as mock_worker_cls,
        patch.object(
            BaseApplication,
            "run",
            autospec=True,
            side_effect=_simulate_master_lifecycle,
        ) as mock_run,
    ):
        run_mod.run_gunicorn(with_bg_worker=True)

    mock_worker_cls.assert_called_once_with()
    mock_run.assert_called_once()
    mock_worker.shutdown.assert_called_once_with()


def test_run_gunicorn_skips_background_worker_by_default():
    with (
        patch.dict(sys.modules, {"main": MagicMock(app=MagicMock())}),
        patch(
            "BG_operations.BackgroundWorker.BackgroundWorker",
        ) as mock_worker_cls,
        patch.object(
            BaseApplication,
            "run",
            autospec=True,
            side_effect=_simulate_master_lifecycle,
        ) as mock_run,
    ):
        run_mod.run_gunicorn()

    mock_worker_cls.assert_not_called()
    mock_run.assert_called_once()


def test_main_gunicorn_with_bg_worker_flag():
    with patch.object(run_mod, "run_gunicorn") as mock_run_gunicorn:
        run_mod.main(["gunicorn", "--with-bg-worker"])

    mock_run_gunicorn.assert_called_once_with(with_bg_worker=True)


def test_main_gunicorn_without_bg_worker_flag():
    with patch.object(run_mod, "run_gunicorn") as mock_run_gunicorn:
        run_mod.main(["gunicorn"])

    mock_run_gunicorn.assert_called_once_with(with_bg_worker=False)
