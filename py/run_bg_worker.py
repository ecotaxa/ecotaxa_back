# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import signal
from threading import Event
from typing import Any

from BG_operations import AllJobServices  # noqa: F401
from BG_operations.BackgroundWorker import BackgroundWorker
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


def _run_background() -> None:
    stop_event = Event()

    def _handle_stop(signum: int, _frame: Any) -> None:
        logger.info("Received signal %d, stopping BackgroundWorker", signum)
        stop_event.set()

    prev_sigint = signal.signal(signal.SIGINT, _handle_stop)
    prev_sigterm = signal.signal(signal.SIGTERM, _handle_stop)

    background_worker = BackgroundWorker()
    logger.info("BackgroundWorker started")
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        background_worker.shutdown()
        logger.info("BackgroundWorker shutdown complete")
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)


if __name__ == "__main__":
    _run_background()
