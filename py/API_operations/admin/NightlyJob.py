# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Maintenance operations on the DB.
#
import os
import time
import shutil
import datetime
from glob import glob
from dataclasses import dataclass
from typing import Tuple, Any, List, Optional

from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from FS.UserFilesDir import UserFilesDirectory
from BO.Job import JobBO
from BO.Project import ProjectBO
from BO.Rights import RightsBO
from BO.Taxonomy import TaxonomyBO
from DB.Job import JobIDT, Job
from DB.Project import Project, ProjectIDListT
from DB.User import Role
from DB.helpers import Result
from DB.helpers import Session
from DB.helpers.Direct import text
from FS.TempDirForTasks import TempDirForTasks
from helpers.DynamicLogs import get_logger, LogsSwitcher
from pathlib import Path

logger = get_logger(__name__)


class NightlyJobService(JobServiceBase):
    """
    Mainly call relevant maintenance SQL and log output.
    """

    JOB_TYPE = "NightlyMaintenance"
    REPORT_EVERY = 20
    NIGHTLY_CHECKS: List["ConsistencyCheckAndFix"] = []
    IDLE_CHECKS: List["ConsistencyCheckAndFix"] = []

    def __init__(self) -> None:
        super().__init__()
        self.curr = 0
        self.trashdirpattern = ""

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
        all_prj_ids = [proj_id for proj_id, in self.ro_session.query(Project.projid)]
        all_prj_ids.sort()
        self.compute_all_projects_taxo_stats(all_prj_ids, 0, 30)
        self.compute_all_projects_stats(all_prj_ids, 30, 60)
        self.refresh_taxo_tree_stats(60)
        self.clean_old_jobs(75)
        const_status = self.check_consistency(80, 90)
        self.users_files_maintenance(90, 100)
        if not const_status:
            self.set_job_result(
                errors=["See log for consistency problems"], infos={"status": "error"}
            )
        else:
            self.set_job_result(errors=[], infos={"status": "ok"})
        self.update_progress(100, "Done")
        logger.info("Job done")

    def stats_progress_update(
        self, start: int, chunk: ProjectIDListT, total: int, end: int
    ) -> None:
        logger.info("Done for %s", chunk)
        self.curr += len(chunk)
        progress = round(start + (end - start) / total * self.curr)
        self.update_progress(progress, "Processing project %d" % chunk[-1])
        chunk.clear()

    def compute_all_projects_taxo_stats(
        self, all_proj_ids: ProjectIDListT, start: int, end: int
    ) -> None:
        """
        Update the summary projects_taxo_stat table, for all projects.
        """
        logger.info("Starting recompute of 'projects_taxo_stat' table")
        chunk = []
        total = len(all_proj_ids)
        for proj_id in all_proj_ids:
            ProjectBO.update_taxo_stats(self.session, proj_id)
            self.session.commit()
            chunk.append(proj_id)
            if len(chunk) == self.REPORT_EVERY:
                self.stats_progress_update(start, chunk, total, end)
        logger.info("Done for %s", chunk)

    def compute_all_projects_stats(
        self, all_proj_ids: ProjectIDListT, start: int, end: int
    ) -> None:
        """
        Recompute relevant fields, directly in projects table.
        Needs @see compute_all_projects_taxo_stats first
        """
        logger.info("Starting recompute of projects' stats columns")
        chunk = []
        total = len(all_proj_ids)
        for proj_id in all_proj_ids:
            ProjectBO.update_stats(self.session, proj_id)
            self.session.commit()
            chunk.append(proj_id)
            if len(chunk) == self.REPORT_EVERY:
                self.stats_progress_update(start, chunk, total, end)
        logger.info("Done for %s", chunk)

    def refresh_taxo_tree_stats(self, start: int) -> None:
        """
        Recompute taxonomy summaries.
        """
        self.update_progress(start, "Recomputing taxonomy stats")
        logger.info("Starting recompute of taxonomy stats")
        TaxonomyBO.compute_stats(self.session)
        self.session.commit()
        logger.info("Recompute of taxonomy stats done")

    def clean_old_jobs(self, start: int) -> None:
        """
        Reclaim space on disk (and in DB) for old jobs.
        Rules: Jobs older than 30 days are erased whatever
               Jobs older than 1 week are erased if they ran OK.
        """
        self.update_progress(start, "Recomputing taxonomy stats")
        logger.info("Starting cleanup of old jobs")
        thirty_days_ago = datetime.datetime.today() - datetime.timedelta(days=30)
        old_jobs_qry_1 = (
            self.ro_session.query(Job.id)
            .filter(Job.id > 0)
            .filter(Job.creation_date < thirty_days_ago)
        )
        old_jobs = [an_id for an_id, in old_jobs_qry_1]
        one_week_ago = datetime.datetime.today() - datetime.timedelta(days=7)
        old_jobs_qry_2 = (
            self.ro_session.query(Job.id)
            .filter(Job.id > 0)
            .filter(Job.creation_date < one_week_ago)
            .filter(Job.state == "F")
        )
        old_jobs_2 = [an_id for an_id, in old_jobs_qry_2]
        to_clean = set(old_jobs).union(set(old_jobs_2))
        logger.info("About to clean %d jobs %s", len(to_clean), to_clean)
        temp_for_job = TempDirForTasks(self.config.jobs_dir())
        for job_id in to_clean:
            # Commit each job, a bit inefficient but in case of trouble we have less de-sync with filesystem
            with JobBO.get_for_update(self.session, job_id) as job_bo:
                temp_for_job.archive_for(job_id, {JobServiceBase.JOB_LOG_FILE_NAME})
                job_bo.archive()
        logger.info("Cleanup of old jobs done")

    def check_consistency(self, start: int, end: int, idle: bool = False) -> bool:
        """Ensure data is how it should be"""
        no_problem = True
        to_run = self.NIGHTLY_CHECKS + (self.IDLE_CHECKS if idle else [])
        total = len(to_run)
        for idx, a_check in enumerate(to_run):
            progress = round(start + (end - start) / total * idx)
            self.update_progress(
                progress, "Checking consistency: %s" % a_check.background
            )
            logger.info("Consistency: %s", a_check.background)
            ok, actual = a_check.verify_ok(self.ro_session)
            if not ok:
                logger.info("Failed: expected %s actual %s", a_check.expected, actual)
                logger.info("Query was: %s", a_check.query)
                logger.info(
                    "_POTENTIAL_ SQL to fix (but better fix root cause): %s",
                    a_check.fix,
                )
                no_problem = False
        return no_problem

    def get_tree_time(self, path: Path, ptime: int) -> int:
        """return max creation time of subdirs in seconds"""
        dtime = ptime
        for entry in os.scandir(path):
            if entry.name[0 : len(self.trashdirpattern)] == self.trashdirpattern:
                continue
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError as error:
                logger.error("Error calling is_dir():", error)
                continue
            if is_dir:
                dtime = int(os.path.getctime(entry.path))

                if ptime > dtime:
                    dtime = self.get_tree_time(Path(entry.path), dtime)
        return dtime

    @staticmethod
    def _delete_definitely(item: Path, tf: int, prefix: Optional[str] = None):
        if prefix is None:
            name = str(item)
        else:
            name = str(item).replace(prefix, "")
        if item.is_dir():
            try:
                shutil.rmtree(item)
                logger.info("Directory '%s' removed '%s'", name, time.ctime(tf))
            except Exception as e:
                logger.error("Error deleting directory '%s' '%s' ", name, str(e))
        else:
            try:
                os.remove(item)
                logger.info("File '%s' removed '%s'", name, time.ctime(tf))
            except Exception as e:
                logger.error("Error deleting file '%s' '%s' ", name, str(e))

    def users_files_maintenance(self, start: int, end: int) -> None:
        """
        delete users directories older than TIME_TO_LIVE
        """
        logger.info("Start Users Files Maintenance")
        self.update_progress(start, "User Files Maintenance")
        timelive: Optional[str] = self.config.get_time_to_live()
        if timelive is None or timelive == "":
            return None
        if int(timelive) > 0:
            # 10 times less for trash to live
            trashlive = int(timelive) / 10
            if trashlive < 1:
                trashlive = 1
        else:
            trashlive = 1
        time_to_live = int(timelive) * 3600 * 24  # in seconds
        trash_to_live = trashlive * 3600 * 24  # in seconds
        usersfiles: Optional[str] = self.config.get_users_files_dir()
        if usersfiles is None:
            return None
        users_files_dir = usersfiles
        logger.info("Starting removing directories older than %s day(s)", str(timelive))
        now = time.time()
        old = now - time_to_live
        old = int(old)
        trashtime = now - trash_to_live
        td = time.ctime(old)
        logger.info("Find and remove directories created before %s", str(td))
        userdirpattern = UserFilesDirectory.USER_DIR_PATTERN.replace("%d", "")
        self.trashdirpattern = UserFilesDirectory.TRASH_DIRECTORY.replace("%d", "")
        # remove trashed dir and files older than trash_to_live
        for entry in glob(
            users_files_dir
            + os.path.sep
            + userdirpattern
            + "*"
            + os.path.sep
            + self.trashdirpattern
            + "*"
            + os.path.sep
            + "*"
        ):
            item = Path(entry)
            tf = int(os.path.getctime(item))
            if tf < trashtime:
                self._delete_definitely(item, tf, users_files_dir)
        # non recursive, only first level directories check and remove as it may lose coherence
        for entry in glob(users_files_dir + os.path.sep + userdirpattern + "*"):
            item = Path(entry)
            if item.is_dir():
                for subdir in os.scandir(item):
                    item = Path(subdir)
                    if item.name[0 : len(self.trashdirpattern)] != self.trashdirpattern:
                        name = str(item).replace(str(users_files_dir), "")
                        if os.path.exists(item):
                            is_dir = item.is_dir()
                            if is_dir:
                                tf = self.get_tree_time(
                                    item, int(os.path.getctime(entry))
                                )
                            else:
                                tf = int(os.path.getctime(item))
                            if tf < old:
                                self._delete_definitely(item, tf, users_files_dir)
        logger.info("End removing directories older than %s day(s)", str(timelive))
        self.update_progress(end, "Users Files Maintenance terminated")
        return None


@dataclass
class ConsistencyCheckAndFix(object):
    background: str
    query: str
    expected: Any
    fix: str

    def verify_ok(self, session: Session) -> Tuple[bool, Any]:
        res: Result = session.execute(text(self.query))
        actual = next(res)[0] if isinstance(self.expected, int) else res.all()
        return actual == self.expected, actual


NightlyJobService.IDLE_CHECKS = [
    ConsistencyCheckAndFix(
        "No job is active",
        "select id from job where state in ('P','R','A')",
        [],
        "need investigation",
    ),
]

# So far just focus on Predicted state as we need consistent data to move to a new system.
NightlyJobService.NIGHTLY_CHECKS = [
    ConsistencyCheckAndFix(
        "In initial blank state there is no ancillary residual info",
        "select count(1) as res from obj_head where classif_qual is null "
        "and (classif_id is not null or classif_date is not null or classif_who is not null or classif_score is not null)",
        0,
        "need investigation",
    ),
    ConsistencyCheckAndFix(
        "There is a (user-visible) category and a date for any non-initial state",
        "select * from obj_head where classif_qual in ('P','V','D') and (classif_id is null or classif_date is null) limit 10",
        [],
        "need investigation",
    ),
    ConsistencyCheckAndFix(
        "There is a state if there is a category",
        "select count(1) from obj_head where classif_qual is null and classif_id is not null",
        0,
        "",
    ),
    ConsistencyCheckAndFix(
        "Validated and Dubious were set by humans, we must know who and when",
        "select count(1) from obj_head where classif_qual in ('V','D') and (classif_who is null or classif_date is null)",
        0,
        """
        -- find root cause
        """,
    ),
    ConsistencyCheckAndFix(
        "The must be no score information for manual states",
        "select objid from obj_head where classif_qual in ('V','D') and classif_score is not null limit 100",
        [],
        """
        -- find root cause
        """,
    ),
    ConsistencyCheckAndFix(
        "Predicted was set by machine, no trailing traces of previous human action",
        "select objid from obj_head where classif_qual = 'P' and (classif_who is not null) limit 100",
        [],
        """update obj_head
set classif_who = NULL
where classif_qual = 'P'
and (classif_who is not null)""",
    ),
    ConsistencyCheckAndFix(
        "No classif_qual nor classif_id but some prediction info",
        "select count(1) from obj_head where classif_qual is null and classif_id is null and classif_score is not null",
        0,
        """update obj_head 
set classif_score=null 
where classif_qual is null and classif_id is null and classif_score is not null""",
    ),
    ConsistencyCheckAndFix(
        "A score is present for 'P', coming from last prediction",
        "select * from obj_head where classif_qual='P' and classif_score is null limit 100",
        [],
        """
        --- find root cause & re-predict
        """,
    ),
    ConsistencyCheckAndFix(
        "All obj_fields have same acquisid as object",
        "select count(1) from obj_head obh join obj_field obf on obf.objfid = obh.objid where obh.acquisid != obf.acquis_id",
        0,
        """
        -- find root cause
        """,
    ),
    ConsistencyCheckAndFix(
        "Only consistent history entries are OK. Auto prediction with a score and manual with someone.",
        """select objid, classif_qual, classif_who, classif_score
    from objectsclassifhisto
    where not ((classif_qual = 'P' and classif_score is not null and classif_who is null) or
               (classif_qual = 'D' and classif_score is null and classif_who is not null) or
               (classif_qual = 'V' and classif_score is null and classif_who is not null)) limit 100""",
        [],
        """
            -- find root cause
            """,
    ),
    ConsistencyCheckAndFix(
        "We must know which prediction a predicted object comes from, in order to move to 'next' "
        "when the prediction is discarded.",
        """select obh.*
    from obj_head obh
    left join prediction prd 
       on prd.object_id = obh.objid 
       and prd.classif_id = obh.classif_id
       and prd.score = obh.classif_score
    where obh.classif_qual = 'P'
      and prd.object_id is null
      limit 100
        """,
        [],
        """
            -- find root cause
            """,
    ),
    ConsistencyCheckAndFix(
        "We must know which training a historical prediction comes from, in order to restore it",
        """select och.*
    from objectsclassifhisto och
    join prediction_histo prh 
       on prh.object_id = och.objid 
       and prh.classif_id = och.classif_id
       and prh.score = och.classif_score
    left join training trn
       on trn.training_id = prh.training_id
    where och.classif_qual = 'P'
      and trn.training_start is null
      limit 100
        """,
        [],
        """
            -- find root cause
            """,
    ),
    ConsistencyCheckAndFix(
        "An object cannot be in a prediction and historical same prediction",
        """select * from prediction_histo prh
     join prediction prd on prh.training_id = prd.training_id
                     and prh.object_id = prd.object_id
      limit 100
        """,
        [],
        """
            -- find root cause
            """,
    ),
    ConsistencyCheckAndFix(
        "Trainings must be consistent in time",
        """select trn.*
    from training trn
    where trn.training_end < trn.training_start
      limit 100
        """,
        [],
        """
            -- find root cause
            """,
    ),
    ConsistencyCheckAndFix(
        "Trainings must not overlap for the same project",
        """select * from training trn
             where exists(select 1 from training trn2 where trn2.projid = trn.projid and trn.training_id != trn2.training_id
                                                  and (trn2.training_start between trn.training_start and trn.training_end
                                                      or trn2.training_end between trn.training_start and trn.training_end))
            limit 100
        """,
        [],
        """
            -- find root cause
            """,
    ),
]
