# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from threading import Event, Thread
from typing import Optional, Union

from API_operations.Prediction import PredictForProject
from BG_operations.JobsManager import JobsManager
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

JOB_INTERVAL = 2


class BackgroundWorker:
    """
    A dedicated thread/process to manage background entities, such as jobs.
    A single instance exists per EcoTaxa app, either in production or in development.
    """

    def __init__(self) -> None:
        JobsManager.FILTER = [PredictForProject.JOB_TYPE]
        self.the_thread: Optional[Thread] = None
        self.stop_event: Event = Event()
        self.launch_at_interval(JOB_INTERVAL)

    def launch_at_interval(self, interval: Union[int, float]) -> None:
        """Launch periodic background worker thread if not already running."""
        if self.the_thread is not None and self.the_thread.is_alive():
            return

        self.stop_event.clear()
        self.the_thread = Thread(
            target=self.run_loop,
            args=(interval,),
            name=f"{self.__class__.__name__}Thread",
            daemon=True,
        )
        self.the_thread.start()

    def run_loop(self, interval: Union[int, float]) -> None:
        """Continuous loop checking for background work."""
        while not self.stop_event.wait(timeout=interval):
            try:
                with JobsManager() as sce:
                    sce.run_one()
            except Exception as e:
                # TODO here we have cryptic startup message if DB issue
                logger.exception("Job run() exception: %s", e)

        # Exiting thread after being signaled to stop
        JobsManager.wait_runner()

    def shutdown(self) -> None:
        """
        Clean close of multi-threading resources: Runner, Thread, and Event.
        """
        self.stop_event.set()
        if self.the_thread is not None:
            if self.the_thread.is_alive():
                self.the_thread.join(timeout=5)
            self.the_thread = None

        JobsManager.shutdown()
