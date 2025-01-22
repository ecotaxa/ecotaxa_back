# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, cast

from API_models.imports import ImportReq, ImportRsp
from API_operations.helpers.JobService import ArgsDict
from API_operations.imports.ImportBase import ImportServiceBase
from BO.Bundle import InBundle
from BO.Classification import ClassifIDT
from BO.Job import JobBO
from BO.Mappings import ProjectMapping
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO
from BO.User import UserIDT, UserBO
from BO.helpers.ImportHelpers import ImportHow, ImportDiagnostic, ImportWhere
from BO.helpers.TSVHelpers import none_to_empty
from DB.Image import Image
from DB.helpers import Session
from DB.helpers.DBWriter import DBWriter
from helpers.DynamicLogs import get_logger, LogsSwitcher
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


class FileImport(ImportServiceBase):
    """
    Before doing the real import, analyze the input in order to prevent issues and give choices
    to user.
    """

    JOB_TYPE = "FileImport"

    MISSING_INFO_MESSAGE = "Some users or taxonomic references could not be matched"

    STATE_KEYS = ["found_users", "taxo_found", "col_mapping", "nb_rows", "source_path"]
    STATE_KEYS_REPLY = ["found_users", "taxo_found"]

    req: ImportReq  # Not used, just for typings

    def __init__(self, prj_id: int, req: ImportReq):
        super().__init__(prj_id, req)

    def init_args(self, args: ArgsDict) -> ArgsDict:
        """Nothing specific so far"""
        return super().init_args(args)

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        # Ensure that the request is OK, if not below will raise as pydantic is quite pydantic :)
        json_args["req"] = ImportReq(**json_args["req"])

    def run(self, current_user_id: int) -> ImportRsp:
        """
        Initial run, basically just create the job.
        """
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.ANNOTATE, self.prj_id)
        # OK, go background straight away
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = ImportRsp(job_id=self.job_id)
        return ret

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
                self.do_validate()
            elif job.progress_msg == JobBO.REPLIED_MESSAGE:
                self.do_complete_and_continue()
            else:
                raise Exception("Not know progress:'%s'" % job.progress_msg)

    def do_complete_and_continue(self) -> None:
        """
        Fill in (hopefully) missing data, before resuming processing if all is OK.
        """
        logger.info("Using reply %s", self.last_reply)
        found_users = self.saved_state["found_users"]
        found_taxa = self.saved_state["taxo_found"]
        self.complete_references(
            found_users, found_taxa, self.last_reply["users"], self.last_reply["taxa"]
        )
        self._save_vars_to_state(self.STATE_KEYS_REPLY, found_users, found_taxa)
        # Assert validity after input
        missing_users, missing_taxa = self.validate_references(found_users, found_taxa)
        if len(missing_users) > 0 or len(missing_taxa) > 0:
            question_data = {
                "missing_users": missing_users,
                "missing_taxa": missing_taxa,
            }
            self.set_job_to_ask(self.MISSING_INFO_MESSAGE, question_data)
        else:
            self.do_real()

    def do_validate(self) -> None:
        """
        Do the real job, i.e. copy files while creating records. Runs in background.
        """
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logger.info("Previously loaded files: %s", loaded_files)
        # Prepare response
        self.update_progress(0, "Validating")
        # Unzip or point to source directory
        job_user_id: UserIDT = self._get_owner_id()
        source_dir_or_zip = self.unzip_if_needed(job_user_id)
        # Validate files
        logger.info("Analyze TSV Files")
        how, diag, nb_rows = self._collect_existing_and_validate(
            source_dir_or_zip, loaded_files, job_user_id
        )
        if len(diag.errors) > 0:
            self.set_job_result(errors=diag.errors, infos={"infos": diag.messages})
            return
        # Resolve identifiers
        self.resolve_references(how.found_users, how.found_taxa)
        # Save all computations so far
        self._save_vars_to_state(
            self.STATE_KEYS,
            how.found_users,
            how.found_taxa,
            how.custom_mapping.as_dict(),
            nb_rows,
            source_dir_or_zip,
        )
        # If anything is missing then we need input from user
        missing_users, missing_taxa = self.validate_references(
            how.found_users, how.found_taxa
        )
        if len(missing_users) > 0 or len(missing_taxa) > 0:
            question_data = {
                "missing_users": missing_users,
                "missing_taxa": missing_taxa,
            }
            self.set_job_to_ask(self.MISSING_INFO_MESSAGE, question_data)
        else:
            self.do_real()

    def _collect_existing_and_validate(
        self, source_dir_or_zip: str, loaded_files: List[str], job_owner: UserIDT
    ) -> Tuple[ImportHow, ImportDiagnostic, int]:
        """
        Prepare the import by checking what's inside the project and scanning files to input.
        """
        # The mapping to TSV custom columns, either empty or from previous import operations on same project.
        mapping = ProjectMapping().load_from_project(self.prj)
        # Source bundle construction
        bundle_temp_dir = Path(self.temp_for_jobs.data_dir_for(self.job_id))
        source_bundle = InBundle(source_dir_or_zip, "[base]", bundle_temp_dir)
        # Configure the validation to come, directives.
        import_how = ImportHow(
            self.prj_id,
            self.req.update_mode,
            mapping,
            self.req.skip_existing_objects,
            loaded_files,
            job_owner,
        )
        if self.req.skip_loaded_files:
            import_how.compute_skipped(source_bundle, logger)
        # A structure to collect validation result
        import_diag = ImportDiagnostic()
        if not self.req.skip_existing_objects:
            with CodeTimer(
                "collect_existing: Existing images for %d: " % self.prj_id, logger
            ):
                import_diag.existing_objects_and_image = Image.fetch_existing_images(
                    self.session, self.prj_id
                )
        import_diag.topology.read_from_db(self.session, prj_id=self.prj_id)
        # Do the bulk job of validation
        nb_rows = source_bundle.validate_import(
            import_how, import_diag, self.session, self.report_validation_progress
        )
        return import_how, import_diag, nb_rows

    def resolve_references(
        self,
        users_found: Dict[str, Dict[str, Any]],
        taxo_found: Dict[str, Optional[int]],
    ):
        """
        We have references inside the TSVs, to users or categories.
        Resolve them and fill in the dicts in arguments.
        """
        logger.info("Resolve users")
        self.resolve_users(self.session, users_found)
        logger.info("Resolve taxonomy")
        self.resolve_taxa(self.session, taxo_found)

    @staticmethod
    def complete_references(
        users_found: Dict[str, Dict[str, Any]],
        taxo_found: Dict[str, Optional[int]],
        more_users: Dict[str, UserIDT],
        more_taxo: Dict[str, ClassifIDT],
    ) -> None:
        """
        Use provided more_* dict for overriding the *_found data.
        """
        for a_user, its_id in more_users.items():
            if a_user in users_found:
                users_found[a_user] = {"id": its_id}
        taxo_found.update(more_taxo)

    @staticmethod
    def validate_references(
        users_found: Dict, taxo_found: Dict[str, Optional[int]]
    ) -> Tuple[List[str], List[str]]:
        """
        After collection of references, ensure completeness.
        """
        missing_users = [k for k, v in users_found.items() if v.get("id") is None]
        missing_taxa = [k for k, v in taxo_found.items() if v is None]
        return missing_users, missing_taxa

    @staticmethod
    def resolve_users(session: Session, users_found: Dict[str, Dict[str, Any]]) -> None:
        """
        Resolve TSV names from DB names or emails.
        :param session:
        :param users_found: The resolve input and output
        """
        names = [x for x in users_found.keys()]
        # TODO: Might be time for a TypedDict
        emails = [
            cast(str, x.get("email")) for x in users_found.values() if x.get("email")
        ]
        UserBO.find_users(session, names, emails, users_found)
        logger.info("Users Found for all TSVs = %s", users_found)

    @staticmethod
    def resolve_taxa(session: Session, taxo_found: Dict[str, Optional[int]]) -> None:
        """
        Resolve taxa names.
        :param taxo_found: The resolve output
        """
        lower_taxon_list = []
        regexsearchparenthese = re.compile(r"(.+) \((.+)\)$")
        taxo_lookup: Dict[str, Dict[str, Any]] = {}
        for taxon_lc in taxo_found.keys():
            taxo_lookup[taxon_lc] = {"nbr": 0, "id": None}
            lower_taxon_list.append(taxon_lc)
            in_regex = regexsearchparenthese.match(taxon_lc)
            if in_regex:
                taxon_lc_lt = in_regex.group(1) + "<" + in_regex.group(2)
                taxo_lookup[taxon_lc]["alterdisplayname"] = taxon_lc_lt
                lower_taxon_list.append(taxon_lc_lt)

        TaxonomyBO.resolve_taxa(session, taxo_lookup, lower_taxon_list)

        logger.info(
            "For all TSVs, taxa (with no ID in TSV) found from DB = %s", taxo_lookup
        )
        for a_ref, found_v in taxo_lookup.items():
            nbr = found_v["nbr"]
            assert isinstance(nbr, int)
            if nbr == 0:
                logger.info("Taxo '%s' Not Found", a_ref)
                taxo_found[a_ref] = None
            elif nbr > 1:
                # more than one is ambiguous, hence like not found
                logger.info("Taxo '%s' Found more than once", a_ref)
                taxo_found[a_ref] = None
            else:
                taxo_found[a_ref] = found_v["id"]
        logger.info("For all TSVs, taxa (with no ID in TSV) resolved = %s", taxo_found)

    def report_validation_progress(self, current: int, total: int) -> None:
        self.update_progress(
            int(20 * current / total), "Validating files %d/%d" % (current, total)
        )

    def do_real(self) -> None:
        """
        Do the real job, i.e. write everywhere (DB/filesystem)
        """
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logger.info("Previously loaded files: %s", loaded_files)

        (
            found_users,
            taxo_found,
            col_mapping_dict,
            nb_rows,
            source_path,
        ) = self._load_vars_from_state(self.STATE_KEYS)
        job_user_id: UserIDT = self._get_owner_id()

        # Save mappings straight away
        col_mapping = ProjectMapping().load_from_dict(col_mapping_dict)
        col_mapping.write_to_project(self.prj)
        self.session.commit()

        # TODO: Duplicated code
        source_bundle = InBundle(
            source_path, "[base]", Path(self.temp_for_jobs.data_dir_for(self.job_id))
        )
        # Configure the import to come, destination
        db_writer = DBWriter(self.session)
        import_where = ImportWhere(
            db_writer, self.vault, self.temp_for_jobs.base_dir_for(self.job_id)
        )
        # Configure the import to come, directives
        import_how = ImportHow(
            self.prj_id,
            self.req.update_mode,
            col_mapping,
            self.req.skip_existing_objects,
            loaded_files,
            job_user_id,
        )
        import_how.taxo_mapping = self.req.taxo_mappings
        import_how.found_taxa = taxo_found
        import_how.found_users = found_users
        if self.req.skip_loaded_files:
            import_how.compute_skipped(source_bundle, logger)
        if self.req.skip_existing_objects:
            # If we must skip existing objects then do an inventory of what's in already
            with CodeTimer("run: Existing images for %d: " % self.prj_id, logger):
                import_how.objects_and_images_to_skip = Image.fetch_existing_images(
                    self.session, self.prj_id
                )
        import_how.do_thumbnail_above(self.config.get_thumbnails_limit())

        # Do the bulk job of import
        rowcount_from_validate = nb_rows
        row_count = source_bundle.do_import(
            import_where, import_how, rowcount_from_validate, self.report_progress
        )

        # Update loaded files in DB, removing duplicates
        self.prj.fileloaded = "\n".join(set(import_how.loaded_files))
        self.session.commit()

        # Recompute stats
        ProjectBO.do_after_load(self.session, self.prj_id)
        self.session.commit()

        msg = "Total of %d rows loaded" % row_count
        logger.info(msg)
        self.set_job_result(errors=[], infos={"rowcount": row_count})
