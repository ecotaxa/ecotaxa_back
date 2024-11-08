# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path
from typing import Tuple, List, Any, Dict, TextIO

from BG_operations.JobScheduler import JobScheduler
from BO.Job import JobBO
from BO.Rights import RightsBO, NOT_FOUND, NOT_AUTHORIZED
from BO.User import UserIDT
from DB.Job import JobIDT, DBJobStateEnum, Job
from DB.User import User, Role
from FS.TempDirForTasks import TempDirForTasks
from helpers.fastApiUtils import AutoCloseBinaryIO
from ..helpers.JobService import JobServiceBase
from ..helpers.Service import Service


class JobCRUDService(Service):
    """
    Basic query API operations on Jobs.
    They share temporary space with historical jobs AKA tasks.
    """

    def list(self, current_user_id: UserIDT, admin_mode: bool) -> List[JobBO]:
        """
        List jobs, if administrator mode then list all of them (for monitoring) else only return the jobs
        owned by caller.
        """
        # current_user = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # assert current_user is not None
        assert not admin_mode or (
            admin_mode and current_user.has_role(Role.APP_ADMINISTRATOR)
        ), NOT_AUTHORIZED
        qry = self.ro_session.query(Job).filter(Job.id > 0)
        if not admin_mode:
            qry = qry.filter(Job.owner_id == current_user_id)
        ret = [JobBO(a_job) for a_job in qry]
        return ret

    def query(self, current_user_id: UserIDT, job_id: JobIDT) -> JobBO:
        """
        Return a single job BO by its id. Users/admin can query archived job if they know how.
        """
        # Sanity & security checks
        job = self.ro_session.query(Job).get(job_id)
        assert job is not None, NOT_FOUND
        # current_user = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # assert current_user is not None
        assert (job.owner_id == current_user_id) or (
            current_user.has_role(Role.APP_ADMINISTRATOR)
        ), NOT_AUTHORIZED
        return JobBO(job)

    def _query_for_update(self, current_user_id: UserIDT, job_id: JobIDT) -> JobBO:
        """
        Return a single job BO, from DB, by its id.
        """
        # Sanity & security checks
        try:
            job = JobBO.get_for_update(self.session, job_id)
        except ValueError:
            assert False, NOT_FOUND
        # current_user = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        # assert current_user is not None
        assert (job.owner_id == current_user_id) or (
            current_user.has_role(Role.APP_ADMINISTRATOR)
        ), NOT_AUTHORIZED
        return job

    def get_file_stream(
        self, current_user_id: UserIDT, job_id: JobIDT
    ) -> Tuple[AutoCloseBinaryIO, str, str]:
        """
        Return a stream containing the produced file associated with this job.
        """
        # Sanity & security checks
        with self._query_for_update(current_user_id, job_id) as job_bo:
            temp_for_job = TempDirForTasks(self.config.jobs_dir())
            temp_dir = temp_for_job.base_dir_for(job_id)
            # Get the job in its state...
            with JobScheduler.instantiate(job_bo) as sce:
                out_file_name = sce.PRODUCED_FILE_NAME
                assert out_file_name is not None
            # ...and the file in its temp directory
            out_file_path = temp_dir / out_file_name
            if out_file_name.endswith(".zip"):
                media_type = "application/zip"
            elif out_file_name.endswith(".tsv"):
                media_type = "text/tab-separated-values"
            else:
                media_type = "unknown"
            fp = AutoCloseBinaryIO(out_file_path)
            return fp, out_file_name, media_type

    def get_log_stream(self, current_user_id: UserIDT, job_id: JobIDT) -> TextIO:
        return open(self.get_log_path(current_user_id, job_id), "r")

    def get_log_path(self, current_user_id: UserIDT, job_id: JobIDT) -> Path:
        # Sanity & security checks
        job: JobBO = self.query(current_user_id, job_id)
        temp_for_job = TempDirForTasks(self.config.jobs_dir())
        log_file_path = (
            temp_for_job.base_dir_for(job.id) / JobServiceBase.JOB_LOG_FILE_NAME
        )
        return log_file_path

    def restart(self, current_user_id: UserIDT, job_id: JobIDT) -> None:
        with self._query_for_update(current_user_id, job_id) as job_bo:
            if job_bo.state not in (DBJobStateEnum.Error,):
                return
            job_bo.state = DBJobStateEnum.Pending
            job_bo.progress_msg = JobBO.RESTARTING_MESSAGE

    def reply(
        self, current_user_id: UserIDT, job_id: JobIDT, reply: Dict[str, Any]
    ) -> None:
        """
        Store a reply to a question 'asked by' the job.
        """
        with self._query_for_update(current_user_id, job_id) as job_bo:
            if job_bo.state not in (DBJobStateEnum.Asking,):
                return
            job_bo.state = DBJobStateEnum.Pending
            job_bo.progress_msg = JobBO.REPLIED_MESSAGE
            job_bo.set_reply(reply)

    def delete(self, current_user_id: UserIDT, job_id: JobIDT) -> None:
        """
        Erase the job, from user's point of view.
        """
        # Security check
        with self._query_for_update(current_user_id, job_id) as job_bo:
            temp_for_job = TempDirForTasks(self.config.jobs_dir())
            if job_bo.state in (
                DBJobStateEnum.Finished,
                DBJobStateEnum.Error,
                DBJobStateEnum.Pending,
            ):
                # TODO: Set the job to a state e.g. Trashed and erase in background, better for responsiveness
                temp_for_job.archive_for(job_id, {JobServiceBase.JOB_LOG_FILE_NAME})
                job_bo.archive()
            elif job_bo.state == DBJobStateEnum.Running:
                # Set the job to Killed
                # TODO: It's not a _real_ kill, bg thread keeps running. It's just presentation
                job_bo.state = DBJobStateEnum.Error
                job_bo.progress_msg = JobBO.KILLED_MESSAGE
