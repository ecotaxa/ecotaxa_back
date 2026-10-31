# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from threading import Event, Thread
from typing import Optional, Union

from API_operations.helpers.Service import Service
from DB.Job import Job
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import regular_mem_cleanup

logger = get_logger(__name__)


class ResourceCleaner(Service):
    """
    In charge of running periodic connection pool and memory cleanups.
    """

    the_thread: Optional[Thread] = None
    stop_event: Event = Event()

    def do_cleanup(self) -> None:
        """
        Run maintenance tasks: ro_session query for connection pool eviction and memory cleanup.
        """
        self.ro_session.query(Job).filter(Job.id == 0).first()
        regular_mem_cleanup()

    @classmethod
    def launch_at_interval(cls, interval: Union[int, float]) -> None:
        """Launch periodic cleanup thread if not already running."""
        if cls.the_thread is not None and cls.the_thread.is_alive():
            return

        cls.stop_event.clear()
        cls.the_thread = Thread(
            target=cls.run_loop,
            args=(interval,),
            name=f"{cls.__name__}Thread",
            daemon=True,
        )
        cls.the_thread.start()

    @classmethod
    def run_loop(cls, interval: Union[int, float]) -> None:
        """Continuous loop running periodic cleanup."""
        # stop_event.wait(timeout) returns True when stop_event.set() is called
        while not cls.stop_event.wait(timeout=interval):
            try:
                with cls() as sce:
                    sce.do_cleanup()
            except Exception as e:
                logger.exception("%s run() exception: %s", cls.__name__, e)

    @classmethod
    def shutdown(cls) -> None:
        """Clean close of multi-threading resources."""
        cls.stop_event.set()
        if cls.the_thread is not None:
            if cls.the_thread.is_alive():
                cls.the_thread.join(timeout=5)
            cls.the_thread = None
