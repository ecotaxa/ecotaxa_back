# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
import logging
import re
import zipfile
from abc import ABC
from os.path import join
from typing import Union, Dict, Optional

from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from BO.helpers.ImportHelpers import ImportHow, ImportDiagnostic, ImportWhere
from api.imports import ImportPrepReq, ImportRealReq, ImportRealRsp, ImportPrepRsp
from db.Image import Image
from db.Object import Object
from db.Project import Project
from db.Sample import Sample
from db.Task import Task
from db.Taxonomy import Taxonomy
from db.User import User
from framework.Service import Service
from fs.TempDirForTasks import TempDirForTasks
from fs.Vault import Vault
from tasks.DBWriter import DBWriter
from utils import none_to_empty

logger = logging.getLogger(__name__)


class ImportServiceBase(Service, ABC):
    """
        Common methods and data for import task steps.
    """
    req: Union[ImportPrepReq, ImportRealReq]
    prj_id: int = 0
    task_id: int = -1

    def __init__(self, prj_id: int, req: Union[ImportPrepReq, ImportRealReq]):
        super().__init__()
        self.prj_id = prj_id
        """ The project ID to import into """
        self.task_id = req.task_id
        self.req = req
        # From legacy code, vault and temptask are in src directory
        self.vault = Vault(join(self.link_src, 'vault'))
        self.temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        # Work vars
        self.prj: Union[Project, None] = None
        self.task: Union[Task, None] = None

    def prepare_run(self):
        """
            Load what's needed for run.
        """
        self.prj = self.session.query(Project).filter_by(projid=self.prj_id).first()
        assert self.prj is not None
        self.task = self.session.query(Task).filter_by(id=self.task_id).first()
        assert self.task is not None

    def update_task(self, taskstate: Optional[str], percent: Optional[int], message: str):
        if taskstate is not None:
            self.task.taskstate = taskstate
        if percent is not None:
            self.task.progresspct = percent
        self.task.progressmsg = message
        self.task.lastupdate = datetime.datetime.now()
        self.session.commit()

    def update_progress(self, percent: int, message: str):
        self.update_task(taskstate=None, percent=percent, message=message)


class ImportAnalysis(ImportServiceBase):
    """
        Before doing the real import, analyze the input in order to prevent issues and give choices
        to user.
    """
    req: ImportPrepReq  # Not used, just for typings

    def __init__(self, prj_id: int, req: ImportPrepReq):
        super().__init__(prj_id, req)
        # Received from parameters
        self.source_dir_or_zip = req.source_path
        # From DB record
        self.intra_step = 0
        self.step_errors = []
        # The row count seen at previous step
        self.total_row_count = 0

    def run(self) -> ImportPrepRsp:
        super().prepare_run()
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logger.info("Previously loaded files: %s", loaded_files)
        # Prepare response
        ret = ImportPrepRsp(source_path=self.source_dir_or_zip)
        self.update_progress(0, "Starting")
        # Unzip or point to source directory
        self.unzip_if_needed()
        ret.source_path = self.source_dir_or_zip
        # Validate files
        logger.info("Analyze TSV Files")
        how, diag, nb_rows = self.do_intra_step_1(loaded_files)
        ret.mappings = how.custom_mapping.as_dict()
        ret.warnings = diag.messages
        ret.errors = diag.errors
        ret.rowcount = nb_rows
        # Resolve users...
        logger.info("Resolve users")
        self.resolve_users(self.session, how.found_users)
        ret.found_users = how.found_users
        # ...and taxonomy
        logger.info("Resolve taxonomy")
        self.resolve_taxa(self.session, how.taxo_found)
        ret.found_taxa = how.taxo_found

        return ret

    def do_intra_step_1(self, loaded_files):
        # The mapping to custom columns, either empty or from previous import operations on same project.
        custom_mapping = ProjectMapping().load_from_project(self.prj)
        # Source bundle construction
        source_bundle = InBundle(self.source_dir_or_zip)
        # Configure the validation to come, directives.
        import_how = ImportHow(self.prj_id, custom_mapping, self.req.skip_existing_objects, loaded_files)
        if self.req.skip_loaded_files:
            import_how.compute_skipped(source_bundle, logger)
        # A structure to collect validation result
        import_diag = ImportDiagnostic()
        if not self.req.skip_existing_objects:
            import_diag.existing_objects_and_image = Image.fetch_existing_images(self.session, self.prj_id)
        # Do the bulk job of validation
        nb_rows = source_bundle.validate_import(self.session, import_how, import_diag)
        return import_how, import_diag, nb_rows

    @staticmethod
    def resolve_users(session, users_found: Dict):
        """
            Resolve TSV names from DB names or emails.
        """
        names = [x for x in users_found.keys()]
        emails = [x.get('email') for x in users_found.values()]
        User.find_users(session, names, emails, users_found)
        logger.info("Users Found for all TSVs = %s", users_found)

    @staticmethod
    def resolve_taxa(session, taxo_found: dict):
        """
            Resolve taxa names.
            :param session:
            :param taxo_found: The resolve output
            :return not found taxa
        """
        lower_taxon_list = []
        regexsearchparenthese = re.compile(r'(.+) \((.+)\)$')
        for taxon_lc in taxo_found.keys():
            taxo_found[taxon_lc] = {'nbr': 0, 'id': None}
            lower_taxon_list.append(taxon_lc)
            in_regex = regexsearchparenthese.match(taxon_lc)
            if in_regex:
                taxon_lc_lt = in_regex.group(1) + '<' + in_regex.group(2)
                taxo_found[taxon_lc]['alterdisplayname'] = taxon_lc_lt
                lower_taxon_list.append(taxon_lc_lt)

        Taxonomy.resolve_taxa(session, taxo_found, lower_taxon_list)

        logger.info("For all TSVs, taxa with no ID found from DB = %s", taxo_found)
        for found_k, found_v in taxo_found.items():
            if found_v['nbr'] == 0:
                logger.info("Taxo '%s' Not Found", found_k)
            elif found_v['nbr'] > 1:
                # more than one is like not found
                logger.info("Taxo '%s' Found more than once", found_k)
                taxo_found[found_k]['id'] = None
        for found_k, found_v in taxo_found.items():
            # in the end we just keep the id, other fields were transitory
            taxo_found[found_k] = found_v['id']
        logger.info("For all TSVs, taxa with no ID resolved = %s", taxo_found)

    def unzip_if_needed(self):
        """
            If a .zip was sent, unzip it. Otherwise it is assumed that we point to an import directory.
        """
        if self.source_dir_or_zip.lower().endswith(".zip"):
            logger.info("SubTask0 : Unzip File into temporary folder")
            self.update_progress(1, "Unzip File into temporary folder")
            input_path = self.source_dir_or_zip
            self.source_dir_or_zip = self.temp_for_task.data_dir_for(self.task_id)
            with zipfile.ZipFile(input_path, 'r') as z:
                z.extractall(self.source_dir_or_zip)


class RealImport(ImportServiceBase):
    """
        Real import, assumes that previous step completed successfully.
    """
    req: ImportRealReq  # Not used, just here for correct typings

    def __init__(self, prj_id: int, req: ImportRealReq):
        super().__init__(prj_id, req)
        #
        self.custom_mapping: Union[Dict, ProjectMapping] = req.mappings

    def run(self) -> ImportRealRsp:
        """
            Do the real job using injected parameters.
            :return:
        """
        super().prepare_run()
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logger.info("Previously loaded files: %s", loaded_files)

        # Transcode from serialized form and save straight away
        self.custom_mapping = ProjectMapping().load_from_dict(self.custom_mapping)
        self.save_mapping(self.custom_mapping)

        source_bundle = InBundle(self.req.source_path)
        # Configure the import to come, destination
        db_writer = DBWriter(self.session)
        import_where = ImportWhere(db_writer, self.vault, self.temp_for_task.base_dir_for(self.task_id))
        # Configure the import to come, directives
        import_how = ImportHow(self.prj_id, self.custom_mapping, self.req.skip_existing_objects, loaded_files)
        import_how.taxo_mapping = self.req.taxo_mappings
        import_how.taxo_found = self.req.found_taxa
        import_how.found_users = self.req.found_users
        if self.req.skip_loaded_files:
            import_how.compute_skipped(source_bundle, logger)
        if not self.req.skip_existing_objects:
            import_how.objects_and_images_to_skip = Image.fetch_existing_images(self.session, self.prj_id)
        import_how.do_thumbnail_above(int(self.config['THUMBSIZELIMIT']))

        # Do the bulk job of import
        row_count = source_bundle.do_import(import_where, import_how, self.req.rowcount, self.report_progress)

        # Update loaded files in DB
        self.prj.fileloaded = "\n".join(import_how.loaded_files)
        self.session.commit()

        # Ensure the ORM has no shadow copy before going to plain SQL
        self.session.expunge_all()
        Object.update_counts_and_img0(self.session, self.prj_id)
        Sample.propagate_geo(self.session, self.prj_id)
        Project.update_taxo_stats(self.session, self.prj_id)
        # Stats depend on taxo stats
        Project.update_stats(self.session, self.prj_id)
        logger.info("Total of %d rows loaded" % row_count)
        # Prepare response
        ret = ImportRealRsp()
        return ret

    def report_progress(self, current, total):
        self.update_progress(100 * current / total,
                             "Processing files %d/%d" % (current, total))

    def save_mapping(self, custom_mapping):
        """
        DB update of mappings for the Project
        """
        custom_mapping.write_to_project(self.prj)
        self.session.commit()
