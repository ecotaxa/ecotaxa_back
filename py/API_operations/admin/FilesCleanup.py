# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Cleanup operations for user files and temporary uploads.
#
import datetime
import os
import shutil
import time
from glob import glob
from pathlib import Path
from typing import List, Optional

from API_operations.helpers.JobService import ArgsDict, JobServiceBase
from BO.Job import JobBO
from BO.Rights import RightsBO
from DB.Job import JobIDT
from DB.User import Role
from FS.Unpack import PROGRESS_PREFIX, UnpackStatus, active_stagings
from FS.Uploads import CLAIM_SUFFIX, get_tus_files_dir, get_tus_info_dir
from FS.UserFilesDir import UserFilesDirectory, get_unpack_registry_dir
from helpers.DynamicLogs import LogsSwitcher, get_logger

logger = get_logger(__name__)

# A TUS upload, or its metadata, untouched for this long (s) can't be retried by the client
TUS_RETRY_AGE = 24 * 3600
# TUS upload metadata files, and their temporary version while written
INFO_SUFFIXES = (".info", ".info.tmp")
# The daily log of the users files removals, after its date
MAINTENANCE_LOG_SUFFIX = "-users_files_maintenance.log"
# An archive extraction folder not registered, untouched for this long (s), is removed
STAGING_ORPHAN_AGE = 24 * 3600


class FilesCleanupService(JobServiceBase):
    JOB_TYPE = "FilesCleanup"
    PROGRESS_LOG_INTERVAL = 60

    def __init__(self, older_than: Optional[int] = None) -> None:
        super().__init__()
        self.trash_dir_pattern = ""
        self.older_than = older_than
        self.deleted_items = 0
        self.last_progress_log = 0.0

    def init_args(self, args: ArgsDict) -> ArgsDict:
        args["older_than"] = self.older_than
        return args

    def run(self, current_user_id: int, older_than: Optional[int] = None) -> JobIDT:
        """Initial creation."""
        RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        if older_than is not None:
            self.older_than = older_than
        self.create_job(self.JOB_TYPE, current_user_id)
        return self.job_id

    def do_background(self) -> None:
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
        logger.info("Files cleanup starting")
        self.update_progress(0, "Starting")
        self.users_files_maintenance(0, 100)
        self.set_job_result(errors=[], infos={"status": "ok"})
        logger.info("Files cleanup done")

    def _delete_definitely(
        self,
        logger_filename: str,
        item: Path,
        tf: int,
        prefix: Optional[str] = None,
    ) -> bool:
        """Remove item, and log it in loggerfilename. Return whether it was removed."""
        if prefix is None:
            name = str(item)
        else:
            name = str(item).replace(prefix, "")
        if item.is_dir():
            try:
                shutil.rmtree(item)
                self._log_cleanup_progress(deleted=True)
                with open(logger_filename, "a", encoding="utf-8") as loggerfile:
                    loggerfile.write(
                        "Directory '%s' removed '%s'\n" % (name, time.ctime(tf))
                    )
            except Exception as e:
                logger.error("Error deleting directory '%s' '%s' ", name, str(e))
                return False
        else:
            try:
                os.remove(item)
                self._log_cleanup_progress(deleted=True)
                with open(logger_filename, "a", encoding="utf-8") as loggerfile:
                    loggerfile.write(
                        "File '%s' removed '%s'\n" % (name, time.ctime(tf))
                    )
            except Exception as e:
                logger.error("Error deleting file '%s' '%s' ", name, str(e))
                return False
        return True

    def _log_cleanup_progress(self, deleted: bool = False) -> None:
        if deleted:
            self.deleted_items += 1
        now = time.monotonic()
        if now - self.last_progress_log >= self.PROGRESS_LOG_INTERVAL:
            logger.info("Files cleanup progress: %d items removed", self.deleted_items)
            self.last_progress_log = now

    def users_files_maintenance(self, start: int, end: int) -> None:
        """
        Delete users directories older than TIME_TO_LIVE.
        """
        self.deleted_items = 0
        self.last_progress_log = time.monotonic()
        logger.info("Start Users Files Maintenance")
        self.update_progress(start, "User Files Maintenance")
        time_to_live_days = (
            self.older_than
            if self.older_than is not None
            else int(self.config.get_time_to_live())
        )
        if time_to_live_days >= 1:
            trash_time_to_live = time_to_live_days / 10
            if trash_time_to_live < 1:
                trash_time_to_live = 1
        else:
            return None
        time_to_live = time_to_live_days * 3600 * 24
        trash_to_live = trash_time_to_live * 3600 * 24
        users_files_dir = self.config.get_users_files_dir()
        today = datetime.datetime.now()
        logger_filename = "%s/%s%s" % (
            users_files_dir,
            today.strftime("%Y-%m-%d"),
            MAINTENANCE_LOG_SUFFIX,
        )
        logger.info(
            "Starting removing directories older than %s day(s)", time_to_live_days
        )
        logger.info(
            "Log file: %s",
            today.strftime("%Y-%m-%d") + MAINTENANCE_LOG_SUFFIX,
        )
        now = time.time()
        old = int(now - time_to_live)
        trash_time = now - trash_to_live
        td = time.ctime(old)
        logger.info("Find and remove directories created before %s", str(td))
        user_dir_pattern = UserFilesDirectory.USER_DIR_PATTERN.replace("%d", "")
        self.trash_dir_pattern = UserFilesDirectory.TRASH_DIRECTORY.replace("%d", "")

        nb_trash, nb_hidden_trash = 0, 0
        for entry in glob(
            users_files_dir
            + os.path.sep
            + user_dir_pattern
            + "*"
            + os.path.sep
            + self.trash_dir_pattern
            + "*"
            + os.path.sep
            + "*",
            include_hidden=True,
        ):
            self._log_cleanup_progress()
            item = Path(entry)
            tf = int(os.path.getctime(item))
            if tf < trash_time:
                if self._delete_definitely(logger_filename, item, tf, users_files_dir):
                    nb_trash += 1
                    if item.name.startswith("."):
                        nb_hidden_trash += 1
        logger.info(
            "Removed %d trash entries older than %s day(s), %d of them hidden",
            nb_trash,
            str(trash_time_to_live),
            nb_hidden_trash,
        )

        extracted_old = int(now - TUS_RETRY_AGE)
        nb_tus_old, nb_tus_extracted = 0, 0
        for entry in glob(get_tus_files_dir() + os.path.sep + "*"):
            self._log_cleanup_progress()
            item = Path(entry)
            tf = int(os.path.getctime(item))
            if tf < old:
                if self._delete_definitely(logger_filename, item, tf, users_files_dir):
                    nb_tus_old += 1
            elif self._extracted_upload(item, extracted_old):
                if self._delete_definitely(logger_filename, item, tf, users_files_dir):
                    nb_tus_extracted += 1
        logger.info(
            "Removed %d TUS upload files older than %s day(s), "
            "and %d extracted more than a day ago",
            nb_tus_old,
            time_to_live_days,
            nb_tus_extracted,
        )

        nb_infos = self._clean_tus_infos(logger_filename, now)
        logger.info("Removed %d TUS upload metadata files without upload", nb_infos)

        active = [
            a_staging.absolute()
            for a_staging in active_stagings(get_unpack_registry_dir())
        ]
        orphan_old = int(now - STAGING_ORPHAN_AGE)
        nb_dirs, nb_orphans = 0, 0
        for entry in glob(users_files_dir + os.path.sep + user_dir_pattern + "*"):
            self._log_cleanup_progress()
            item = Path(entry)
            if not item.is_dir():
                continue
            paths_to_delete = []
            for root, dirs, files in os.walk(entry, topdown=False):
                for a_dir in dirs:
                    self._log_cleanup_progress()
                    if a_dir.startswith(self.trash_dir_pattern):
                        continue
                    dirpath = Path(root).joinpath(a_dir)
                    if self._holds_extraction(dirpath, active):
                        continue
                    too_old = orphan_old if a_dir.startswith(PROGRESS_PREFIX) else old
                    ptime = int(os.path.getctime(dirpath))
                    if ptime < too_old:
                        if self._can_delete_dir(
                            str(dirpath), too_old, self.trash_dir_pattern
                        ):
                            paths_to_delete.append((dirpath, ptime))

            for dirpath, ptime in paths_to_delete:
                self._log_cleanup_progress()
                if self._delete_definitely(
                    logger_filename, dirpath, ptime, users_files_dir
                ):
                    if dirpath.name.startswith(PROGRESS_PREFIX):
                        nb_orphans += 1
                    else:
                        nb_dirs += 1
        logger.info(
            "Removed %d directories older than %s day(s), "
            "and %d orphan archive extraction folders",
            nb_dirs,
            time_to_live_days,
            nb_orphans,
        )

        nb_logs = self._clean_maintenance_logs(users_files_dir, old)
        logger.info(
            "Removed %d users files maintenance logs older than %s day(s)",
            nb_logs,
            time_to_live_days,
        )
        logger.info("End removing directories older than %s day(s)", time_to_live_days)
        logger.info("Files cleanup removed %d items in total", self.deleted_items)
        self.update_progress(end, "Users Files Maintenance terminated")

    @staticmethod
    def _extracted_upload(item: Path, too_old: int) -> bool:
        upload_id = item.name
        if "." in upload_id:
            return False
        try:
            if not item.is_file():
                return False
            if not Path(get_tus_files_dir(), upload_id + CLAIM_SUFFIX).exists():
                return False
            status = UnpackStatus.read(upload_id)
            if status is None or status.get("state") != "done":
                return False
            return int(os.path.getctime(UnpackStatus.path_for(upload_id))) < too_old
        except (ValueError, OSError):
            return False

    @staticmethod
    def _holds_extraction(dirpath: Path, active: List[Path]) -> bool:
        abs_path = dirpath.absolute()
        return any(
            a_staging == abs_path or abs_path in a_staging.parents
            for a_staging in active
        )

    def _clean_maintenance_logs(self, users_files_dir: str, too_old: int) -> int:
        ret = 0
        pattern = users_files_dir + os.path.sep + "*" + MAINTENANCE_LOG_SUFFIX
        for entry in glob(pattern):
            self._log_cleanup_progress()
            try:
                if int(os.path.getctime(entry)) >= too_old:
                    continue
                os.remove(entry)
                self._log_cleanup_progress(deleted=True)
                ret += 1
            except OSError as e:
                logger.error("Error deleting file '%s' '%s' ", entry, str(e))
        return ret

    def _clean_tus_infos(self, loggerfilename: str, now: float) -> int:
        info_dir = get_tus_info_dir()
        try:
            entries = list(os.scandir(info_dir))
        except OSError:
            return 0
        tus_dir = get_tus_files_dir()
        ret = 0
        for an_entry in entries:
            self._log_cleanup_progress()
            name = an_entry.name
            if name.startswith(".") or not name.endswith(INFO_SUFFIXES):
                continue
            try:
                if not an_entry.is_file(follow_symlinks=False):
                    continue
                mtime = an_entry.stat(follow_symlinks=False).st_mtime
            except OSError:
                continue
            upload_id = name.split(".", 1)[0]
            if os.path.lexists(os.path.join(tus_dir, upload_id)):
                continue
            if now - mtime < TUS_RETRY_AGE:
                continue
            if self._delete_definitely(
                loggerfilename, Path(an_entry.path), int(mtime), info_dir
            ):
                ret += 1
        return ret

    def _can_delete_dir(self, start_path: str, ptime: int, excluded: str) -> bool:
        for root, dirs, files in os.walk(start_path, topdown=True):
            for a_file in files:
                self._log_cleanup_progress()
                filepath = Path(root).joinpath(a_file)
                tf = int(os.path.getctime(filepath))
                if tf >= ptime:
                    return False
            for a_dir in dirs:
                self._log_cleanup_progress()
                if a_dir.startswith(excluded):
                    continue
                dirpath = Path(root).joinpath(a_dir)
                tf = int(os.path.getctime(dirpath))
                if tf >= ptime:
                    return False
        return True
