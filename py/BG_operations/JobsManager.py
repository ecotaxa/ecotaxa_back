# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import multiprocessing as mp
import os
import signal
import threading
from multiprocessing.connection import wait as mp_wait
from threading import Thread
from typing import Any, Optional, List, Type, Union, ClassVar

from sqlalchemy import select

from API_operations.helpers.JobService import JobServiceBase
from API_operations.helpers.Service import Service
from BO.Job import JobBO
from DB.Job import Job, DBJobStateEnum, JobIDT
from DB.helpers.ORM import clone_of
from helpers import DateTime
from helpers.DevMode import is_debug_mode, is_pytest
from helpers.DynamicLogs import (
    get_logger,
    LogsSwitcher,
)

logger = get_logger(__name__)

spawn_ctx = mp.get_context("spawn")

MAX_PARALLEL_JOBS = 8


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
            raise ValueError(msg)
        self.db_job = a_db_job
        self.sce_class = sce_class

    def common_run(self, msg: str) -> None:
        """
        Common run logic for both Thread and Process runners.
        """
        try:
            sce = JobsManager.instantiate(self.sce_class, self.db_job)
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
        with (
            Service() as base_service
        ):  # Use a fresh session, in case the problem comes from the service session
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
        Run the background part of the service. Present code executes in the subprocess.
        """
        null_fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(null_fd, 0)  # stdin
        os.dup2(null_fd, 1)  # stdout
        if is_pytest():
            os.dup2(null_fd, 2)  # stderr is left for upper process, in case.
        os.close(null_fd)

        # Re-init loggers, now useless due to spawn()
        # DynamicLogs.rewire_loggers_after_fork()

        # Launch the job
        self.common_run(f"PID {os.getpid()}")


JobRunnerType = Union[Type[ThreadJobRunner], Type[ProcessJobRunner]]
JobRunner: JobRunnerType = ProcessJobRunner
# Force thread in debug
if is_debug_mode():
    JobRunner = ThreadJobRunner


class JobsManager(Service):
    """
    In charge of launching/monitoring sub processes i.e. keep sync b/w processes and their images in jobs DB table.
    """

    # Filter out these job types
    FILTER: ClassVar[List[str]] = []
    # Include only these job types
    INCLUDE: ClassVar[List[str]] = []
    # Active runners per web process / background worker.
    the_runners: ClassVar[List[Union[ThreadJobRunner, ProcessJobRunner]]] = []

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def _reap_finished_runners(cls) -> None:
        """Join and interpret any runners that have already finished."""
        still_running: List[Union[ThreadJobRunner, ProcessJobRunner]] = []
        for runner in cls.the_runners:
            if runner.is_alive():
                still_running.append(runner)
            else:
                runner.join()
                cls._interpret_runner_result(runner)
        cls.the_runners = still_running

    def fail_running_jobs(self) -> None:
        """
        Set state of any Running jobs (with positive id) to Error.
        Called when BackgroundWorker starts to clean up orphaned jobs from a previous run.
        """
        stmt = select(Job).where(Job.id > 0, Job.state == DBJobStateEnum.Running)
        if self.INCLUDE:
            stmt = stmt.where(Job.type.in_(tuple(self.INCLUDE)))
        for a_type in self.FILTER:
            stmt = stmt.where(Job.type != a_type)
        stmt = stmt.with_for_update(skip_locked=True)
        running_jobs: List[Job] = list(self.session.scalars(stmt).all())
        if not running_jobs:
            return
        now = DateTime.now_time()
        for a_job in running_jobs:
            logger.warning(
                "Job #%d was in Running state on worker startup; marking as Error",
                a_job.id,
            )
            a_job.state = DBJobStateEnum.Error
            a_job.progress_msg = "Background worker restarted"
            a_job.updated_on = now
        self.session.commit()

    def run_one(self) -> None:
        """
        Pick pending jobs and run them in parallel, up to MAX_PARALLEL_JOBS.
        This is an instance method, so there is DB session to work with, released straight away.
        """
        cls = JobsManager
        cls._reap_finished_runners()

        available_slots = MAX_PARALLEL_JOBS - len(cls.the_runners)
        if available_slots <= 0:
            return

        # Pick pending jobs which are not already managed by another runner
        stmt = select(Job).where(Job.id > 0, Job.state == DBJobStateEnum.Pending)
        if self.INCLUDE:
            stmt = stmt.where(Job.type.in_(tuple(self.INCLUDE)))
        for a_type in self.FILTER:
            stmt = stmt.where(Job.type != a_type)
        stmt = (
            stmt.order_by(Job.id)
            .limit(available_slots)
            .with_for_update(skip_locked=True)
        )
        jobs_to_run: List[Job] = list(self.session.scalars(stmt).all())
        if not jobs_to_run:
            return

        for to_run in jobs_to_run:
            logger.info("Found job to run: %s", str(to_run))
            # Align DB job state
            to_run.state = DBJobStateEnum.Running
        self.session.commit()

        for to_run in jobs_to_run:
            # Detach the job DB line from session, as JobRunner is in another process/thread
            # and SQLAlchemy objects are linked to sessions, and sessions cannot be shared b/w processes.
            job_clone = clone_of(to_run)
            job_clone.id = to_run.id
            try:
                # Run the service background
                runner = JobRunner(JobBO(job_clone))
                runner.start()
            except Exception as e:
                logger.error("Error starting job %d: %s", to_run.id, e)
                BaseJobRunner.tech_error(to_run.id, e)
            else:
                cls.the_runners.append(runner)

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

        exit_msg: Optional[str] = None
        match exitcode:
            case 0 | None:
                pass
            case int(code) if code < 0:
                sig_num = -code
                try:
                    sig_name = signal.Signals(sig_num).name
                    exit_msg = f"Process terminated by signal {sig_num} ({sig_name})"
                except (ValueError, AttributeError):
                    exit_msg = f"Process terminated by signal {sig_num}"
                logger.error("Job #%d: %s", job_id, exit_msg)
            case int(code) if code > 0:
                exit_msg = f"Process failed with exit code {code}"
                logger.error("Job #%d: %s", job_id, exit_msg)
            case _:
                logger.warning(
                    "Job #%d runner completed with unexpected exit code: %s",
                    job_id,
                    exitcode,
                )

        try:
            with Service() as base_service:
                the_job = base_service.session.get(Job, job_id)
                if the_job is None:
                    return  # Someone stole our job
                match the_job.state:
                    case DBJobStateEnum.Running:
                        msg = exit_msg or "Process ended unexpectedly"
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
    def wait_runners(cls) -> None:
        """Wait for all active runners to finish when stopping the scheduler loop."""
        while cls.the_runners:
            cls._reap_finished_runners()
            if not cls.the_runners:
                break
            process_runners = [
                r for r in cls.the_runners if isinstance(r, ProcessJobRunner)
            ]
            if len(process_runners) == len(cls.the_runners):
                mp_wait([r.sentinel for r in process_runners])
            else:
                cls.the_runners[0].join(timeout=0.1)

    @classmethod
    def shutdown(cls) -> None:
        """
        Clean close of any remaining runners during worker shutdown.
        """
        remaining: List[Union[ThreadJobRunner, ProcessJobRunner]] = []
        for runner in cls.the_runners:
            if isinstance(runner, ThreadJobRunner):
                runner.join(timeout=1)
                if runner.is_alive():
                    logger.error(
                        "Job #%d thread did not finish within 1s during shutdown",
                        runner.db_job.id,
                    )
                    remaining.append(runner)
                else:
                    cls._interpret_runner_result(runner)
            else:
                if not runner.is_alive():
                    runner.join(timeout=1)
                    cls._interpret_runner_result(runner)
                else:
                    logger.info(
                        "Job #%d detached process left running during worker shutdown",
                        runner.db_job.id,
                    )
                    remaining.append(runner)
        cls.the_runners = remaining
