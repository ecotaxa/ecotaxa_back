# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import multiprocessing as mp
import os
import signal
import sys
import threading
from threading import Event, Thread
from typing import Any, Optional, List, ClassVar, Callable, Type, Union

from API_operations.helpers.JobService import JobServiceBase
from API_operations.helpers.Service import Service
from BO.Job import JobBO
from DB.Job import Job, DBJobStateEnum, JobIDT
from DB.helpers.ORM import clone_of
from helpers import DynamicLogs
from helpers.DynamicLogs import (
    get_logger,
    LogsSwitcher,
)

logger = get_logger(__name__)

spawn_ctx = mp.get_context("spawn")


class BaseJobRunner:
    """
    Common logic for running background part of a job.
    """

    def __init__(self, a_db_job: JobBO):
        # Get class to run
        sce_class = JobServiceBase.find_jobservice_class_by_type(a_db_job.type)
        if sce_class is None:
            msg = "Found %s in DB and could not match to a Service" % a_db_job.type
            logger.error(msg)
            assert sce_class is not None, msg
        self.db_job = a_db_job
        self.sce_class = sce_class

    def common_run(self, msg: str) -> None:
        """
        Common run logic for both Thread and Process runners.
        """
        try:
            sce = JobScheduler.instantiate(self.sce_class, self.db_job)
            with LogsSwitcher(sce):
                logger.info("Running job %d in %s", self.db_job.id, msg)
        except Exception as te:
            logger.error(f"Error instantiating job {self.db_job.id}: {te}")
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
        with Service() as base_service:
            the_job = base_service.session.get(Job, job_id)
            if the_job is not None:
                the_job.state = DBJobStateEnum.Error
                the_job.progress_msg = str(te)
                base_service.session.commit()


class ThreadJobRunner(Thread, BaseJobRunner):
    """
    Run background part of a job in a Thread.
    """

    def __init__(self, a_db_job: JobBO):
        Thread.__init__(self, name="Job #%d" % a_db_job.id)
        BaseJobRunner.__init__(self, a_db_job)

    def run(self) -> None:
        """
        Run the background part of the service.
        """
        self.common_run(f"Thread {os.getpid()}/{threading.current_thread().ident}")


class ProcessJobRunner(spawn_ctx.Process, BaseJobRunner):  # type: ignore[name-defined]
    """
    Run background part of a job in a process using isolated spawn context.
    """

    def __init__(self, a_db_job: JobBO):
        spawn_ctx.Process.__init__(self, name="Job #%d" % a_db_job.id)
        BaseJobRunner.__init__(self, a_db_job)
        self.daemon = False

    def run(self) -> None:
        """
        Run the background part of the service.
        """
        null_fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(null_fd, 0)
        os.dup2(null_fd, 1)
        os.dup2(null_fd, 2)
        os.close(null_fd)

        # Re-init loggers
        DynamicLogs.rewire_loggers_after_fork()

        # Launch the job
        self.common_run(f"PID {os.getpid()}")


JobRunnerType = Union[Type[ThreadJobRunner], Type[ProcessJobRunner]]
JobRunner: JobRunnerType = ProcessJobRunner
# Force thread in debug
if sys.gettrace() is not None:
    JobRunner = ThreadJobRunner


class JobScheduler(Service):
    """
    In charge of launching/monitoring sub processes i.e. keep sync b/w processes and their images in jobs DB table.
    """

    # Filter out these job types
    FILTER: ClassVar[List[str]] = []
    # Include only these job types
    INCLUDE: ClassVar[List[str]] = []
    # A single runner per web process
    the_runner: Optional[Union[ThreadJobRunner, ProcessJobRunner]] = (
        None  # Only written by JobTimer_s_
    )
    the_timer: Optional[threading.Timer] = None
    # First creation by Main, replacements by JobTimer_s_
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
            cls.the_runner.join()
            cls._interpret_runner_result(cls.the_runner)
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
        # Detach the job DB line from session, as JobRunner is in another process/thread
        # and SQLAlchemy objects are linked to sessions, and sessions cannot be shared b/w processes.
        job_clone = clone_of(the_job)
        job_clone.id = the_job.id
        # Run the service background
        cls.the_runner = JobRunner(JobBO(job_clone))
        cls.the_runner.start()

    @staticmethod
    def instantiate(sce_class: Type["JobServiceBase"], a_job: JobBO):
        # Load the service creation arguments
        assert a_job.params is not None
        sce_class.deser_args(a_job.params)
        # Check arguments against current PID if relevant
        # Note: we do it here as it's common to all runners
        params = a_job.params
        try:
            sce = sce_class(**params)
        except Exception as e:
            logger.error(f"Error instantiating {sce_class}: {e}")
            raise
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
        cls.the_timer.name = "JobTimer"
        cls.the_timer.start()

    @classmethod
    def _interpret_runner_result(
        cls, runner: Union[ThreadJobRunner, ProcessJobRunner]
    ) -> None:
        """
        Interpret the result of waiting for a subprocess or thread runner,
        log its completion status, and reconcile the database job record
        if it ended unexpectedly without completing.
        """
        job_id = runner.db_job.id
        exitcode: Optional[int] = getattr(
            runner, "exitcode", None
        )  # Will be None for threads

        match exitcode:
            case 0 | None:
                pass
            case int(code) if code < 0:
                sig_num = -code
                try:
                    sig_name = signal.Signals(sig_num).name
                    logger.error(
                        "Job #%d process was terminated by signal %d (%s)",
                        job_id,
                        sig_num,
                        sig_name,
                    )
                except (ValueError, AttributeError):
                    logger.error(
                        "Job #%d process was terminated by signal %d", job_id, sig_num
                    )
            case int(code) if code > 0:
                logger.error("Job #%d process failed with exit code %d", job_id, code)
            case _:
                logger.warning(
                    "Job #%d runner completed with unexpected exit code: %s",
                    job_id,
                    exitcode,
                )

        try:
            with Service() as base_service:
                the_job = base_service.session.get(Job, job_id)
                assert the_job is not None
                match the_job.state:
                    case DBJobStateEnum.Running:
                        match exitcode:
                            case int(code) if code < 0:
                                sig_num = -code
                                try:
                                    sig_name = signal.Signals(sig_num).name
                                    msg = f"Process terminated by signal {sig_num} ({sig_name})"
                                except (ValueError, AttributeError):
                                    msg = f"Process terminated by signal {sig_num}"
                            case int(code) if code > 0:
                                msg = f"Process failed with exit code {code}"
                            case _:
                                msg = "Process ended unexpectedly"

                        the_job.state = DBJobStateEnum.Error
                        the_job.progress_msg = msg
                        base_service.session.commit()
                        logger.error(
                            "Job #%d ended unexpectedly while in Running state. Updated state to Error: %s",
                            job_id,
                            msg,
                        )
                    case DBJobStateEnum.Finished | DBJobStateEnum.Error:
                        pass
                    case other_state:
                        logger.warning(
                            "Job #%d in unexpected DB state: %s",
                            job_id,
                            other_state,
                        )
        except Exception as e:
            logger.exception("Error interpreting result for job %d: %s", job_id, e)

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
                # Wait for child process indefinitely before taking another task
                cls.the_runner.join()
                cls._interpret_runner_result(cls.the_runner)
                cls.the_runner = None
            cls.the_timer = None
        else:
            cls._create_and_launch_timer(interval)

    @classmethod
    def shutdown(cls) -> None:
        """
        Clean close of multi-threading resources: Runner, Timer, and Event
        Restore class-loading time state.
        Current thread: Main
        """
        if cls.do_run.is_set():
            # Signal the timer to stop & cancel itself
            cls.do_run.clear()
            # Cancel the timer if it's waiting
            if cls.the_timer:
                cls.the_timer.cancel()
                cls.the_timer = None

        # Also ensure the runner is joined if it was finished or we are shutting down
        if cls.the_runner is not None:
            if not cls.the_runner.is_alive():
                cls.the_runner.join(timeout=1)
                cls._interpret_runner_result(cls.the_runner)
                cls.the_runner = None
            else:
                # If it's still alive, we might want to wait a bit or just leave it
                # but for tests, we should probably try to join it
                cls.the_runner.join(timeout=2)
                if not cls.the_runner.is_alive():
                    cls._interpret_runner_result(cls.the_runner)
                    cls.the_runner = None
                else:
                    logger.warning("JobScheduler runner is still alive during shutdown")
