# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import threading
import time
from threading import Thread, Event
from typing import Any, Optional, List, ClassVar, Callable

from API_operations.helpers.JobService import JobServiceBase
from API_operations.helpers.Service import Service
from BO.Job import JobBO
from DB.Job import Job, DBJobStateEnum, JobIDT
from DB.helpers.ORM import clone_of
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class JobRunner(Thread):
    """
    Run background part of a job.
    """

    def __init__(self, a_db_job: JobBO):
        super().__init__(name="Job #%d" % a_db_job.id)
        self.db_job = a_db_job

    def run(self) -> None:
        """
        Run the background part of the service.
        """
        try:
            sce = JobScheduler.instantiate(self.db_job)
        except (AssertionError, TypeError, json.decoder.JSONDecodeError) as te:
            self.tech_error(self.db_job.id, te)
            return
        with sce:
            sce.run_in_background()

    @staticmethod
    def tech_error(job_id: JobIDT, te: Any) -> None:
        """
        Technical problem, which cannot be managed by the service as it was not possible
        to create it. Report here.
        """
        session = Service().session
        the_job = session.query(Job).get(job_id)
        assert the_job is not None
        the_job.state = DBJobStateEnum.Error
        the_job.progress_msg = str(te)
        session.commit()


class JobScheduler(Service):
    """
    In charge of launching/monitoring sub processes i.e. keep sync b/w processes and their images in jobs DB table.
    These are not really processes, just threads, so far.
    """

    # Filter out these job types
    FILTER: ClassVar[List[str]] = []
    # Include only these job types
    INCLUDE: ClassVar[List[str]] = []
    # A single runner per process
    the_runner: Optional[JobRunner] = None  # Only written by JobTimer_s_
    the_timer: Optional[
        threading.Timer
    ] = None  # First creation by Main, replacements by JobTimer_s_
    do_run: Event = Event()  # R/W by Main & JobTimer
    todo_on_idle: Optional[Callable] = None

    def __init__(self) -> None:
        super().__init__()

    def _run_one(self) -> None:
        """
        Pick first pending job and run it, except if already running.
        This is an instance method, so there is DB session to work with, released straight away.
        Current thread: JobTimer
        """
        cls = JobScheduler
        if cls.the_runner is not None:
            # A single runner at a time
            if cls.the_runner.is_alive():
                return
            cls.the_runner = None
        # Pick the first pending job which is not already managed by another runner
        qry = (
            self.session.query(Job)
            .filter(Job.id > 0)
            .filter(Job.state == DBJobStateEnum.Pending)
        )
        if self.INCLUDE:
            qry = qry.filter(Job.type.in_(tuple(self.INCLUDE)))
        for a_type in self.FILTER:
            qry = qry.filter(Job.type != a_type)
        qry = qry.with_for_update(skip_locked=True)
        the_job: Optional[Job] = qry.first()
        if the_job is None:
            # Exercise the ro_session for Connection pool cleanup
            self.ro_session.query(Job).filter(Job.id == 0).first()
            if cls.todo_on_idle is not None:
                cls.todo_on_idle()
            return
        logger.info("Found job to run: %s", str(the_job))
        # Align DB job state
        the_job.state = DBJobStateEnum.Running
        self.session.commit()
        # Detach the job DB line from session, as JobRunner is in another thread
        # and SQLAlchemy objects are linked to sessions, and sessions cannot be shared b/w threads.
        job_clone = clone_of(the_job)
        job_clone.id = the_job.id
        # Run the service background
        cls.the_runner = JobRunner(JobBO(job_clone))
        cls.the_runner.start()

    @staticmethod
    def instantiate(a_job: JobBO):
        sce_class = JobServiceBase.find_jobservice_class_by_type(
            JobServiceBase, a_job.type
        )
        if sce_class is None:
            msg = "Found %s in DB and could not match to a Service" % a_job.type
            logger.error(msg)
            assert sce_class is not None, msg
        # Load the service creation arguments
        assert a_job.params is not None
        sce_class.deser_args(a_job.params)
        sce = sce_class(**a_job.params)
        # Inject the service state
        sce.load_state_from(a_job.inside)
        sce.load_reply_from(a_job.reply)
        # TODO: Direct member assignment is bad
        sce.job_id = a_job.id
        return sce

    @classmethod
    def launch_at_interval(cls, interval: int) -> None:
        """
        Launch a job if possible, then wait a bit before accessing next one.
        Current thread: Main for first launch, JobTimer (_different ones_) for others
        """
        cls.do_run.set()
        cls._create_and_launch_timer(interval)

    @classmethod
    def _create_and_launch_timer(cls, interval: int) -> None:
        cls.the_timer = threading.Timer(
            interval=interval, function=cls.launch, args=[interval]
        )
        cls.the_timer.setName("JobTimer")
        cls.the_timer.start()

    @classmethod
    def launch(cls, interval: int) -> None:
        # Current thread: JobTimer_s_
        try:
            with cls() as sce:
                # noinspection PyProtectedMember
                sce._run_one()
        except Exception as e:
            # TODO here we have cryptic startup message if DB issue
            logger.exception("Job run() exception: %s", e)
        if not cls.do_run.is_set():
            if cls.the_runner is not None:
                cls.the_runner.join()
                cls.the_runner = None
            cls.the_timer = None
        else:
            cls._create_and_launch_timer(interval)

    @classmethod
    def shutdown(cls) -> None:
        """
        Clean close of multi-threading resources: Runner, Timer and Event
        Restore class-loading time state.
        Current thread: Main
        """
        if cls.do_run.is_set():
            # Signal the timer to stop & cancel itself
            cls.do_run.clear()
            # Wait for it gone
            while cls.the_timer is not None:
                time.sleep(1)
