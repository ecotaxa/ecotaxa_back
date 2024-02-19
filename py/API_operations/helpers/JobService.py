# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import abc
from abc import ABC
from datetime import datetime
from typing import List, Dict, Any, Optional

from BO.Job import JobBO
from BO.User import UserIDT
from DB.Job import Job, JobIDT, DBJobStateEnum
from DB.Project import Project, ProjectIDT
from FS.TempDirForTasks import TempDirForTasks
from helpers.DynamicLogs import get_logger, LogEmitter, LogsSwitcher
from helpers.exception import format_exception
from .Service import Service

logger = get_logger(__name__)

ArgsDict = Dict[str, Any]


class JobServiceBase(Service, LogEmitter, ABC):
    """
    Common methods and data for asynchronous and long operations.
    This base class is for the short-lived instances which 'just' do some operations.
    For long-lived objects, i.e. processes/threads @see JobScheduler class.
    """

    JOB_TYPE: str  # To override in subclasses
    JOB_LOG_FILE_NAME = "TaskLogBack.txt"

    def __init__(self) -> None:
        super().__init__()
        super(LogEmitter, self).__init__()
        self.job_id: JobIDT = 0
        self.temp_for_jobs = TempDirForTasks(self.config.jobs_dir())
        # The state for multi-step jobs
        self.saved_state: Dict[str, Any] = {}
        # The last reply for interactive jobs
        self.last_reply: Dict[str, Any] = {}

    @staticmethod
    def find_jobservice_class_by_type(clazz, job_type: str):
        """
        Find a subclass with given type
        """
        for job_sub_class in clazz.__subclasses__():
            if job_sub_class.JOB_TYPE == job_type:
                return job_sub_class
            else:
                for_subclass = JobServiceBase.find_jobservice_class_by_type(
                    job_sub_class, job_type
                )
                if for_subclass:
                    return for_subclass

    def log_file_path(self) -> str:
        """
        Return redirected logging output path. @see DynamicLogs and LogEmitter.
        """
        log_file = self.temp_for_jobs.base_dir_for(self.job_id) / self.JOB_LOG_FILE_NAME
        return log_file.as_posix()

    @abc.abstractmethod
    def do_background(self) -> None:
        """Launch background processing"""
        pass

    def run_in_background(self):
        """
        Background part of the job, standard behavior is to run the method and care for general problems.
        """
        try:
            self.do_background()
        except Exception as e:
            # If the exception damaged the session, we might end up in:
            # sqlalchemy.exc.InternalError: (psycopg2.errors.InFailedSqlTransaction)
            self.session.rollback()
            with JobBO.get_for_update(self.session, self.job_id) as job_bo:
                job_bo.state = DBJobStateEnum.Error
                job_bo.progress_msg = str(e)
                job_bo.set_messages(format_exception(e))
            with LogsSwitcher(self):
                logger.error("Unexpected termination of #%d", job_bo.id)
                logger.exception(e)

    @abc.abstractmethod
    def init_args(self, args: ArgsDict) -> ArgsDict:
        """Serialization of __init__ arguments"""
        ...

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        pass

    def _save_vars_to_state(self, names: List[str], *values):
        """Save variables using provided names"""
        to_save = {a_name: a_value for a_name, a_value in zip(names, values)}
        with JobBO.get_for_update(self.session, self.job_id) as job_bo:
            job_bo.update_inside(to_save)
        self.saved_state = job_bo.inside

    def _load_vars_from_state(self, names: List[str]) -> List[Any]:
        """Load variables using provided names"""
        ret = [self.saved_state[a_name] for a_name in names]
        return ret

    def load_state_from(self, job_state: Dict[str, Any]) -> None:
        """Injection of service state"""
        self.saved_state = job_state

    def load_reply_from(self, job_reply: Dict[str, Any]) -> None:
        """Injection of service reply to last question"""
        self.last_reply = job_reply

    def create_job(self, job_type: str, user_id: UserIDT):
        args = self.init_args({})
        # Add a pending job, to pick by runner thread, @see JobScheduler.py
        new_job = JobBO.create_job(user_id, job_type, args)
        self.session.add(new_job)
        # self.session.commit() # Uncomment to see the race condition in def test_log_file_exists_if_job_exists
        self.session.flush(
            [new_job]
        )  # Flush sends the SQL to PG, so we can get the id from sequence
        self.job_id = new_job.id
        self.temp_for_jobs.erase_for(new_job.id)  # mainly for tests
        with LogsSwitcher(self):
            logger.info("Creating job %d", self.job_id)
        self.session.commit()

    def _get_job(self) -> Job:
        job: Optional[Job] = self.session.query(Job).get(self.job_id)
        assert job is not None
        return job

    def _get_owner_id(self) -> UserIDT:
        job: Optional[Job] = self.session.query(Job).get(self.job_id)
        assert job is not None
        return job.owner_id

    def get_job_for_update(self) -> Job:
        job = self._get_job()
        job.updated_on = datetime.now()
        return job

    def update_progress(self, percent: int, message: str):
        with JobBO.get_for_update(self.session, self.job_id) as job_bo:
            job_bo.progress_pct = percent
            job_bo.progress_msg = message

    def report_progress(self, current, total):
        self.update_progress(
            20 + 80 * current / total, "Processing files %d/%d" % (current, total)
        )

    def set_job_result(self, errors: List[str], infos: Dict[str, Any]):
        """
        Set job detailed result and final status, then does a DB commit on session.
        """
        with JobBO.get_for_update(self.session, self.job_id) as job_bo:
            job_bo.set_result(infos)
            # Limit storage to 1000 first errors
            job_bo.set_messages(errors[:1000])
            if len(errors) > 0:
                job_bo.state = DBJobStateEnum.Error
                job_bo.progress_msg = "%d error(s) during run" % len(errors)
            else:
                job_bo.state = DBJobStateEnum.Finished
                job_bo.progress_pct = 100
                job_bo.progress_msg = "Done"

    def get_job_result(self) -> Any:
        """
        Get job detailed result.
        """
        job_bo = JobBO.get_one(self.session, self.job_id)
        assert job_bo is not None
        return job_bo.get_result()

    def set_job_to_ask(self, message: str, question_data: Dict[str, Any]):
        """
        Set the job to ask something from user.
        """
        logger.info("Asking for: %s", question_data)
        with JobBO.get_for_update(self.session, self.job_id) as job_bo:
            job_bo.state = DBJobStateEnum.Asking
            job_bo.progress_msg = message
            job_bo.set_question(question_data)


class JobServiceOnProjectBase(JobServiceBase, ABC):
    """
    Common data for asynchronous and long operations, on a specific project.
    """

    JOB_TYPE = ""

    def __init__(self, prj_id: ProjectIDT):
        super().__init__()
        self.prj_id: ProjectIDT = prj_id
        # Work vars, load straight away
        prj = self.get_session().query(Project).get(prj_id)
        assert prj is not None
        self.prj = prj

    def init_args(self, args: Dict) -> Dict:
        """Amend init args, for dynamic creation"""
        args["prj_id"] = self.prj_id
        return args
