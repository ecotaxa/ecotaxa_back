# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
import json
import logging
import re
import zipfile
from os.path import join
from typing import Union, Set, Dict

from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from BO.helpers.ImportHelpers import ImportHow, ImportDiagnostic, ImportWhere
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


class ImportServiceBase(Service):
    """
        Common methods and data for import task steps.
    """

    def __init__(self):
        super().__init__()
        # From legacy code, vault and temptask are in src directory
        self.vault = Vault(join(self.link_src, 'vault'))
        self.temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        # Parameters
        self.prj_id: int = -1
        self.task_id: int = -1

        self.custom_mapping: Union[ProjectMapping, None] = None

        self.taxo_mapping: dict = {}
        self.taxo_found = {}
        self.users_found = {}

        # Choose a folder or zip file on the server
        #  OR
        # Upload folder(s) compressed as a zip file
        self.source_dir_or_zip: str = ""

        # Skip tsv files that have already been imported
        self.skip_already_loaded_file: str = "N"
        # Skip objects that have already been imported
        self.skip_object_duplicate: str = "N"

        # Work vars
        self.prj: Union[Project, None] = None
        self.task: Union[Task, None] = None

    def update_param(self):
        if hasattr(self, 'param'):
            self.task.inputparam = json.dumps(self.param.__dict__)
        self.task.lastupdate = datetime.datetime.now()
        self.session.commit()

    def update_progress(self, percent: int, message: str):
        self.task.progresspct = percent
        self.task.progressmsg = message
        self.update_param()

    @staticmethod
    def log_for_user(msg: str):
        # TODO
        print(msg)
        pass

    def prepare_run(self):
        """
            Load what's needed for run.
        """
        self.prj = self.session.query(Project).filter_by(projid=self.prj_id).first()
        self.task = self.session.query(Task).filter_by(id=self.task_id).first()


class ImportAnalysis(ImportServiceBase):
    """
        Before doing the real import, analyze the input in order to prevent issues and give choices
        to user.
    """

    def __init__(self):
        super().__init__()
        # Received from parameters
        self.intra_step = 0
        self.step_errors = []
        # Where the input data is
        self.input_path: str = ""
        # The row count seen at previous step
        self.total_row_count = 0

    def run(self):
        super().prepare_run()
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logger.info("Previously loaded files: %s", loaded_files)

        not_found_user = {}
        not_found_taxo = {}
        if self.intra_step == 0:
            # Subtask 1, unzip or point to source directory
            self.update_progress(1, "Unzip File into temporary folder")
            self.unzip_if_needed()
            self.intra_step = 1

        if self.intra_step == 1:
            # Validate files
            logger.info("SubTask1 : Analyze TSV Files")
            if self.do_intra_step_1(loaded_files):
                # If anything went wrong we loop on this state
                self.intra_step = 2

        if self.intra_step == 2:
            logger.info("Start Sub Step 1.2")
            # Resolve users...
            not_found_user = self.resolve_users(self.session, self.users_found)
            if len(not_found_user) > 0:
                logger.info("Some Users Not Found = %s", not_found_user)
            # ...and taxonomy
            not_found_taxo = self.resolve_taxa(self.session, self.taxo_found)
            if len(not_found_taxo) > 0:
                logger.info("Some Taxo Not Found = %s", not_found_taxo)

            # # raise Exception("TEST")
            # if len(not_found_user) == 0 and len(not_found_taxo) == 0 and len(warn_messages) == 0:
            #     # all OK, proceed straight away to step2
            #     # TODO
            #     pass
            #     # self.SPStep2()
            # else:
            #     self.task.taskstate = "Question"
            # if len(warn_messages) > 0:
            #     self.update_progress(1, "Unzip File on temporary folder")
            # else:
            #     self.update_progress(1, "Unzip File on temporary folder")
            # sinon on pose une question
        # Prepare response in pure text
        resp = {"prj": self.prj_id,
                "tsk": self.task_id,
                "src": self.source_dir_or_zip,
                "map": self.custom_mapping.as_dict(),
                "nfu": not_found_user,
                "nft": not_found_taxo,
                "wrn": []}  # TODO
        return json.dumps(resp)

    def do_intra_step_1(self, loaded_files):
        # The mapping to custom columns, either empty or from previous import operations
        self.custom_mapping = ProjectMapping().load_from_project(self.prj)
        # Source bundle construction
        source_bundle = InBundle(self.source_dir_or_zip)
        # Configure the validation to come, directives.
        import_how = ImportHow(self.prj_id, self.custom_mapping, self.skip_object_duplicate == 'Y', loaded_files)
        if self.skip_already_loaded_file == 'Y':
            import_how.compute_skipped(source_bundle)
        # A structure to collect validation result
        import_diag = ImportDiagnostic()
        # Do the bulk job of validation
        row_count = source_bundle.validate_import(self.session, import_how, import_diag)
        # Feedback to user
        if len(import_diag.errors) > 0:
            self.task.taskstate = "Error"
            self.task.progressmsg = "Some errors were found during file parsing "
            logger.error(self.task.progressmsg)
            self.session.commit()
            return False
        return True

    @staticmethod
    def resolve_users(session, users_found: Dict) -> [str]:
        """
            Resolve TSV names from DB names or emails.
        """
        names = [x for x in users_found.keys()]
        emails = [x.get('email') for x in users_found.values()]
        User.find_users(session, names, emails, users_found)
        logger.info("Users Found = %s", users_found)
        not_found_users = [k for k, v in users_found.items() if v.get("id") is None]
        return not_found_users

    @staticmethod
    def resolve_taxa(session, taxo_found) -> [str]:
        """
            Resolve taxa names.
            :param session:
            :param taxo_found: The resolve output
            :return not found taxa
        """
        lower_taxon_list = []
        not_found_taxo = []
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

        logger.info("Taxo Found = %s", taxo_found)
        for found_k, found_v in taxo_found.items():
            if found_v['nbr'] == 0:
                logger.info("Taxo '%s' Not Found", found_k)
                not_found_taxo.append(found_k)
            elif found_v['nbr'] > 1:
                # more than one is like not found
                logger.info("Taxo '%s' Found more than once", found_k)
                not_found_taxo.append(found_k)
                taxo_found[found_k]['id'] = None
        for found_k, found_v in taxo_found.items():
            # in the end we just keep the id, other fields were transitory
            taxo_found[found_k] = found_v['id']
        return not_found_taxo

    def fetch_existing_images(self, do_it: bool) -> Set:
        if do_it:
            return Image.fetch_existing_images(self.session, self.prj_id)
        else:
            return set()

    def unzip_if_needed(self):
        if self.input_path.lower().endswith("zip"):
            logger.info("SubTask0 : Unzip File into temporary folder")
            self.update_progress(1, "Unzip File into temporary folder")
            self.source_dir_or_zip = self.temp_for_task.data_dir_for(self.task_id)
            with zipfile.ZipFile(self.input_path, 'r') as z:
                z.extractall(self.source_dir_or_zip)
        else:
            self.source_dir_or_zip = self.input_path


class RealImport(ImportServiceBase):

    def __init__(self, json_params: str):
        super().__init__()
        # Received from parameters
        params = json.loads(json_params)
        # TODO a clean interface
        self.prj_id = params["prj"]
        self.task_id = params["tsk"]
        self.source_dir_or_zip = params["src"]
        self.custom_mapping = ProjectMapping().load_from_dict(params["map"])
        # The row count seen at previous step
        self.total_row_count = 0

    def run(self):
        """
            Do the real job using injected parameters.
            :return:
        """
        super().prepare_run()
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logger.info("Previously loaded files: %s", loaded_files)

        self.save_mapping()
        source_bundle = InBundle(self.source_dir_or_zip)
        # Configure the import to come, destination
        db_writer = DBWriter(self.session)
        import_where = ImportWhere(db_writer, self.vault, self.temp_for_task.base_dir_for(self.task_id))
        # Configure the import to come, directives
        import_how = ImportHow(self.prj_id, self.custom_mapping, self.skip_object_duplicate == 'Y', loaded_files)
        import_how.taxo_found = self.taxo_found
        import_how.taxo_mapping = self.taxo_mapping
        import_how.found_users = self.users_found
        if self.skip_already_loaded_file == 'Y':
            import_how.compute_skipped(source_bundle)
        if self.skip_object_duplicate == 'Y':
            import_how.objects_and_images_to_skip = Image.fetch_existing_images(self.session, self.prj_id)
        import_how.do_thumbnail_above(int(self.config['THUMBSIZELIMIT']))

        # Do the bulk job of import
        row_count = source_bundle.do_import(import_where, import_how)

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

    def save_mapping(self):
        """
        DB update of mappings for the Project
        """
        self.custom_mapping.write_to_project(self.prj)
        self.session.commit()
