# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import time
from pathlib import Path
from typing import List, Union, Set, Dict, Optional, Callable

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
        self.messages: List[str] = []
        self.errors: List[str] = []
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
        self.taxo_mapping = {}
        self.skip_object_duplicates = skip_object_duplicates
        # The maximum image dimension before a thumbnail gets generated
        self.max_dim: int = int(1e10)
        # Mappings, collected during ImportAnalysis and read during RealImport
        self.custom_mapping: ProjectMapping = custom_mapping
        # TODO: for validating it's !=
        self.found_users = {}
        # The taxa _names_ found in TSV _without ID_, key = taxon NAME (str), value = None during analysis
        self.taxo_found = {}
        # Collected during RealImport
        self.existing_parent_ids: Union[Dict, None] = None
        self.existing_objects: Optional[Dict[str, int]] = None
        # Updated during RealImport
        self.loaded_files = loaded_files
        # For UVP6 vignetting
        self.vignette_maker = None

    def do_thumbnail_above(self, max_dim):
        self.max_dim = max_dim

    def compute_skipped(self, bundle, logger):
        """
            Compute files _not_ to load.
        """
        for relative_name in bundle.possible_files_as_posix():
            if relative_name in self.loaded_files:
                self.files_not_to_import.add(relative_name)


class ImportStats(object):
    """
        During an import, the statistics for reporting progress.
    """

    def __init__(self, total_rows: int, report_def: Optional[Callable] = None):
        self.start_time = time.time()
        self.total_row_count = total_rows
        self.current_row_count = 0
        self.report_def = report_def

    def add_rows(self, nb_rows: int):
        self.current_row_count += nb_rows

    def so_far(self):
        elapsed = time.time() - self.start_time
        rows_per_sec = int(self.current_row_count / elapsed)
        return elapsed, rows_per_sec

    def report(self, current):
        if not self.report_def:
            return
        self.report_def(current, self.total_row_count)
