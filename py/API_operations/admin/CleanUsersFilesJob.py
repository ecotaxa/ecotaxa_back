# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Maintenance operations on the DB.
#
import os
import time
import shutil
from typing import Iterator, Tuple, List, Any, Optional
from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from BO.Job import JobBO
from BO.Rights import RightsBO
from DB.Job import JobIDT
from DB.User import Role
from helpers.DynamicLogs import get_logger, LogsSwitcher
from FS.UserFilesDir import UserFilesDirectory

logger = get_logger(__name__)


class CleanUsersFilesJobService(JobServiceBase):
    """
    remove files in users' directories when the quota for each is reached.
    """

    JOB_TYPE = "UsersFilesMaintenance"
    REPORT_EVERY = 20

    def __init__(self) -> None:
        super().__init__()
        self.curr = 0

    def init_args(self, args: ArgsDict) -> ArgsDict:
        """No job param"""
        return args

    def run(self, current_user_id: int) -> JobIDT:
        """
        Initial creation.
        """
        # Security check
        _user = RightsBO.user_has_role(
            self.ro_session, current_user_id, Role.APP_ADMINISTRATOR
        )
        # Security OK, create pending job
        self.create_job(self.JOB_TYPE, current_user_id)
        return self.job_id

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            job = self._get_job()
            if job.progress_msg in (
                None,
                JobBO.PENDING_MESSAGE,
                JobBO.RESTARTING_MESSAGE,
            ):
                self.do_start()
            else:
                raise Exception("Not know progress:'%s'" % job.progress_msg)

    def do_start(self) -> None:
        logger.info("Job starting")
        self.update_progress(0, "Starting")
        try:
            self.clean_my_files()
            self.set_job_result(errors=[], infos={"status": "ok"})
        except Exception as e:
            print("error---", e)
            self.set_job_result(
                errors=["See log for consistency problems"], infos={"status": "error"}
            )
        self.update_progress(100, "Done")
        logger.info("Job done")

    def clean_my_files(self) -> None:
        """
        delete users directories older than TIME_TO_LIVE
        """
        timelive: Optional[str] = self.config.get_users_files_life()
        if timelive is None:
            return
        time_to_live = int(timelive) * 3600 * 24  # in seconds
        usersfiles: Optional[str] = self.config.get_users_files_dir()
        if usersfiles is None:
            return
        users_files_dir = usersfiles
        logger.info("Starting removing directories")
        now = time.time()
        old = now - time_to_live
        old = int(old)
        td = time.ctime(old)

        logger.info("Find and remove directories created before %s", str(td))
        logger.info("root directory '%s'", str(users_files_dir))
        items: Iterator[Tuple[str, List[Any], List[Any]]] = os.walk(
            users_files_dir, topdown=True
        )
        for item in items:
            root: str = item[0]
            dirs: List[str] = item[1]
            if len(dirs) == 0:
                break
            for a_dir in dirs:
                if a_dir is None:
                    continue
                try:
                    _ = a_dir.index(
                        UserFilesDirectory.USER_DIR_PATTERN.replace("%d", "")
                    )

                except ValueError:
                    try:
                        _ = a_dir.index(
                            UserFilesDirectory.TRASH_DIRECTORY.replace("%d", "")
                        )
                    except ValueError:
                        dirname = os.path.join(str(root), str(a_dir))
                        if os.path.exists(dirname):
                            tf = int(os.path.getctime(dirname))
                            if tf < old:
                                try:
                                    shutil.rmtree(dirname)
                                    logger.info(
                                        "Removed '%s' created on %s ",
                                        (dirname, str(time.ctime(tf))),
                                    )
                                except Exception as e:
                                    logger.error(e)
