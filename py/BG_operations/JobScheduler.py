# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import threading
from threading import Thread
from typing import Any, Optional

from API_operations.helpers.JobService import JobServiceBase
from API_operations.helpers.Service import Service
from BO.Job import JobBO
from DB import Job
from DB.Job import DBJobStateEnum, JobIDT
from DB.helpers.ORM import Query, clone_of
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class JobRunner(Thread):
    """
        Run background part of a job.
    """

    def __init__(self, a_db_job: JobBO):
        super().__init__(name="Job #%d" % a_db_job.id)
        self.db_job = a_db_job

    def run(self):
        """
           Run the background part of the service.
        """
        try:
            sce = JobScheduler.instantiate(self.db_job)
            # TODO: Direct member assignment is bad
            sce.job_id = self.db_job.id
        except (AssertionError, TypeError, json.decoder.JSONDecodeError) as te:
            self.tech_error(self.db_job.id, te)
            return
        with sce:
            sce.run_in_background()

    @staticmethod
    def tech_error(job_id: JobIDT, te: Any):
        session = Service().session
        the_job = session.query(Job).get(job_id)
        assert the_job is not None
        the_job.state = DBJobStateEnum.Error
        the_job.progress_msg = str(te)
        session.commit()


class JobScheduler(Service):
    """
        In charge of launching/monitoring sub processes i.e. keep sync b/w processes and their images in jobs DB table.
    """
    # A single runner per process
    the_runner: Optional[JobRunner] = None
    the_timer: Optional[threading.Timer] = None

    def __init__(self):
        super().__init__()

    def run_one(self):
        """
            Pick first pending job and run it, except if already running.
        """
        if self.the_runner is not None:
            # A single runner at a time
            if self.the_runner.is_alive():
                return
        qry: Query = self.session.query(Job).filter(Job.state == DBJobStateEnum.Pending).limit(1)
        qry = qry.with_for_update(nowait=True)
        try:
            the_job: Job = qry.first()
        except:
            return
        if the_job is None:
            return
        logger.info("Found job to run: %s", str(the_job))
        # Align DB job state
        the_job.state = DBJobStateEnum.Running
        self.session.commit()
        # Detach the job DB line from session, as JobRunner is in another thread
        # and objects are linked to sessions, and sessions cannot be shared
        job_clone = clone_of(the_job)
        job_clone.id = the_job.id
        # Run the service background
        self.the_runner = JobRunner(JobBO(job_clone))
        self.the_runner.start()

    def wait_for_stable(self):
        # Not to use outside tests
        self.the_runner.join()

    @staticmethod
    def instantiate(a_job: JobBO):
        sce_class = JobServiceBase.find_jobservice_class_by_type(JobServiceBase, a_job.type)
        if sce_class is None:
            msg = "Found %s in DB and could not match to a Service" % a_job.type
            logger.error(msg)
            assert sce_class is not None, msg
        # Load the service creation arguments
        assert a_job.params
        sce_class.deser_args(a_job.params)
        sce = sce_class(**a_job.params)
        # Inject the service state
        sce.load_state_from(a_job.inside)
        sce.load_reply_from(a_job.reply)
        return sce

    @classmethod
    def is_sane_on_shutdown(cls) -> bool:
        """ Ensure that nothing runs before shutdown """
        if cls.the_runner is None:
            return True
        if cls.the_runner.is_alive():
            return False
        return True

    @classmethod
    def launch_at_interval(cls, interval: int):
        """
            Launch a job if possible, then wait a bit before accessing next one.
        """
        def launch():
            with cls() as sce:
                sce.run_one()
            cls.launch_at_interval(interval)

        cls.the_timer = threading.Timer(interval=interval, function=launch)
        cls.the_timer.start()

    @classmethod
    def shutdown(cls):
        cls.the_timer.cancel()
