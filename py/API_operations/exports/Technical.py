# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Technical PG dump-like export of a single project.
#
from pathlib import Path
from typing import Optional

from API_models.exports import ExportRsp
from BO.Rights import RightsBO, Action
from BO.technical.TechDump import TechnicalDump
from DB.Project import ProjectIDT
from helpers.DynamicLogs import get_logger, LogsSwitcher
from ..helpers.JobService import JobServiceBase, ArgsDict

logger = get_logger(__name__)


class Technical(JobServiceBase):
    """
    Job service producing a PostgreSQL COPY-based dump of all database rows belonging to a single project
    and its vault images, packaged as a zstd-compressed tar archive (.tar.zst).
    """

    JOB_TYPE = "TechnicalExport"

    def __init__(
        self,
        project_id: ProjectIDT,
    ):
        super().__init__()
        self.project_id: ProjectIDT = int(project_id)
        self.out_file_name: str = ""
        self.out_path: Path = Path("")

    def check_rights(self, current_user_id: int) -> None:
        RightsBO.user_wants_export(
            self.session, current_user_id, Action.ADMINISTRATE, self.project_id
        )

    @staticmethod
    def archive_filename(project_id: ProjectIDT) -> str:
        return TechnicalDump.archive_filename(project_id)

    def run(self, current_user_id: int) -> ExportRsp:
        """
        Initial run: check permissions and create the pending job.
        """
        self.check_rights(current_user_id)
        self.create_job(self.JOB_TYPE, current_user_id)
        return ExportRsp(job_id=self.job_id)

    def init_args(self, args: ArgsDict) -> ArgsDict:
        args["project_id"] = self.project_id
        return args

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        json_args["project_id"] = int(json_args["project_id"])

    # noinspection PyPep8Naming
    @property
    def PRODUCED_FILE_NAME(self) -> Optional[str]:
        result = self.get_job_result()
        if result is None:
            return None
        return result["out_file"]

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_export()

    def do_export(self) -> None:
        """
        The real job.
        """
        self.out_path = self.temp_for_jobs.base_dir_for(self.job_id)
        self.out_file_name = self.archive_filename(self.project_id)

        logger.info(
            "Dumping %d: Starting TechnicalExport",
            self.project_id,
        )
        produced_path = self.out_path / self.out_file_name
        dumper = TechnicalDump(self.project_id, self.config.vault_dir())
        row_counts = dumper.dump_project(
            produced_path,
            progress_start=1,
            progress_end=99,
            progress_cb=self.update_progress,
            extra_files=[(Path(self.log_file_path()), f"job_{self.job_id}.log")],
        )

        self.update_progress(100, "Export successful")
        total_rows = sum(row_counts.values())
        self.set_job_result(
            errors=[],
            infos={
                "out_file": self.out_file_name,
                "rowcount": total_rows,
                "tables": row_counts,
            },
        )
