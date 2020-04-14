# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
from pathlib import Path
from typing import List, Union, Set, Dict

from BO.Mappings import ProjectMapping
from fs.Vault import Vault
from tasks.DBWriter import DBWriter


class ImportDiagnostic(object):
    """
        During an import analysis, data and problems collected.
    """

    def __init__(self):
        # record fields for which some values are present
        self.cols_seen = set()
        # taxonomy ids @see Taxonomy
        self.classif_id_seen = set()
        self.nb_objects_without_gps = 0
        self.messages = []
        self.errors = []
        self.existing_objects_and_image = set()

    def warn(self, message: str):
        self.messages.append(message)

    def error(self, message: str):
        self.errors.append(message)


class ImportWhere(object):
    """
        During an import, where to put data, i.e. DB and Images
    """

    def __init__(self, db_writer: Union[DBWriter, None], vault: Vault, temp: Path):
        self.db_writer = db_writer
        self.vault = vault
        self.temp_dir = temp


class ImportHow(object):
    """
        During an import, how to do it, special cases, mappings and so on.
    """

    def __init__(self, prj_id, custom_mapping: ProjectMapping, skip_object_duplicates: bool, loaded_files: List[str]):
        self.prj_id = prj_id
        # From user choices
        self.files_not_to_import = set()
        self.objects_and_images_to_skip: Set = set()
        self.skip_object_duplicates = skip_object_duplicates
        # The maximum image dimension before a thumbnail gets generated
        self.max_dim: int = int(1e10)
        # Mappings
        self.custom_mapping: ProjectMapping = custom_mapping
        # TODO: for validate it's !=
        self.found_users = {}
        self.taxo_found = {}
        self.taxo_mapping = {}
        # Collected during import
        self.existing_parent_ids: Union[Dict, None] = None
        self.existing_objects: Union[Set, None] = None
        # Updated during import
        self.loaded_files = loaded_files
        # For UVPV6 vignetting
        self.vignette_maker = None

    def do_thumbnail_above(self, max_dim):
        self.max_dim = max_dim

    def compute_skipped(self, bundle):
        """
            Compute files _not_ to load.
        """
        for relative_name in bundle.possible_files_as_posix():
            if relative_name in self.loaded_files:
                logging.info("File %s will be skipped, already loaded" % relative_name)
                self.files_not_to_import.add(relative_name)
