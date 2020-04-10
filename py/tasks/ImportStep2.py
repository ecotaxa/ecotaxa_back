# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import logging

from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from db.Object import Object
from db.Project import Project
from db.Sample import Sample
from utils import none_to_empty
from .DBWriter import DBWriter
from .ImportBase import ImportBase


# noinspection PyPackageRequirements


class ImportStep2(ImportBase):

    def __init__(self, json_params: str):
        super(ImportStep2, self).__init__()
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
        super(ImportStep2, self).prepare_run()
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logging.info("loaded_files = %s", loaded_files)
        self.save_mapping()
        source_bundle = InBundle(self.source_dir_or_zip)
        db_writer = DBWriter(self.session)
        if self.skip_already_loaded_file == 'Y':
            for relative_name in source_bundle.possible_files_as_posix():
                if relative_name in loaded_files:
                    logging.info("File %s will be skipped, already loaded" % relative_name)
                    source_bundle.dont_import(relative_name)
        # Do the bulk job of import
        row_count = source_bundle.do_import(self, self.prj_id, db_writer, self.custom_mapping,
                                            self.ignore_duplicates == 'Y',
                                            loaded_files)

        # Update loaded files in DB
        self.prj.fileloaded = "\n".join(loaded_files)
        self.session.commit()
        # Ensure the ORM has no shadow copy before going to plain SQL
        self.session.expunge_all()
        Object.update_counts_and_img0(self.session, self.prj_id)
        Sample.propagate_geo(self.session, self.prj_id)
        Project.update_taxo_stats(self.session, self.prj_id)
        # Stats depend on taxo stats
        Project.update_stats(self.session, self.prj_id)
        logging.info("Total of %d rows loaded" % row_count)

    def save_mapping(self):
        """
        DB update of mappings for the Project
        """
        self.custom_mapping.write_to_project(self.prj)
        self.session.commit()
