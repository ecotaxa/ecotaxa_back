# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import time
from pathlib import Path
from typing import List, Set, Dict, Optional, Callable, Tuple, Any

from BO.Classification import ClassifIDT
from BO.Mappings import ProjectMapping
from BO.ProjectTidying import ProjectTopology
from BO.User import UserIDT
from BO.Vignette import VignetteMaker
from DB.Acquisition import Acquisition
from DB.Sample import Sample
from DB.helpers.DBWriter import DBWriter
from FS.Vault import Vault


class ImportDiagnostic(object):
    """
    During an import analysis, data and problems collected.
    """

    def __init__(self) -> None:
        # record fields for which some values are present
        self.cols_seen: Set[str] = set()
        # taxonomy ids @see Taxonomy
        self.classif_id_seen: Set[ClassifIDT] = set()
        self.nb_objects_without_gps = 0
        self.messages: List[str] = []
        self.errors: List[str] = []
        # existing objects for consistency checks
        self.existing_objects_and_image: Set[str] = set()
        self.topology = ProjectTopology()
        # the files which were found but skipped
        self.skipped_files: List[str] = []

    def warn(self, message: str):
        self.messages.append(message)

    def error(self, message: str):
        self.errors.append(message)


class ImportWhere(object):
    """
    During an import, where to put data, i.e. DB and Images
    """

    def __init__(self, db_writer: DBWriter, vault: Vault, temp: Path):
        self.db_writer = db_writer
        self.vault = vault
        self.temp_dir = temp


class ImportHow(object):
    """
    During an import, how to do it, special cases, mappings and so on.
    """

    def __init__(
        self,
        prj_id,
        update_mode: str,
        custom_mapping: ProjectMapping,
        skip_object_duplicates: bool,
        loaded_files: List[str],
        user_id: UserIDT
    ):
        self.prj_id = prj_id
        # Update or create
        # In this mode, no creation of anything, only update
        self.can_update_only = update_mode in ("Yes", "Cla")
        self.update_with_classif = update_mode == "Cla"
        # From user choices
        self.files_not_to_import: Set[str] = set()
        self.objects_and_images_to_skip: Set[str] = set()
        self.taxo_mapping: Dict[str, str] = {}
        self.skip_object_duplicates = skip_object_duplicates
        # The maximum image dimension before a thumbnail gets generated
        self.max_dim: int = int(1e10)
        # Mappings, collected during ImportAnalysis and read during RealImport
        self.custom_mapping: ProjectMapping = custom_mapping
        # TODO: for validating it's !=
        # The users found in analyzed TSVs, key = name, value = dict with 'email' and/or user 'id'
        self.found_users: Dict[str, Dict[str, Any]] = {}
        # The taxa/category _names_ found in TSV _without ID_,
        #     key = taxon NAME (str), value = None during analysis, id during resolve
        self.found_taxa: Dict[str, Optional[int]] = {}
        # Collected during RealImport
        # e.g. { 'samples': { 'm106_mn01_n2': <Sample object at xxxx> } }
        self.existing_samples: Dict[str, Sample] = {}
        self.existing_acquisitions: Dict[Tuple[str, str], Acquisition] = {}
        # e.g. { 'm106_mn01_n1_sml_409': 1455263 }
        self.existing_objects: Dict[str, int] = {}
        # The generated/from TSV image ranks.
        # e.g. { 1455263 : { 1, 2} }
        self.image_ranks_per_obj: Dict[int, Set[int]] = {}
        # Updated during RealImport
        self.loaded_files = loaded_files
        # For UVP6 vignetting
        self.vignette_maker: Optional[VignetteMaker] = None
        # In case we need to default a user
        self.user_id: UserIDT = user_id

    def do_thumbnail_above(self, max_dim: int) -> None:
        self.max_dim = max_dim

    def compute_skipped(self, bundle, _logger) -> None:
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

    def __init__(self, total_rows: int, report_def: Callable):
        self.start_time = time.time()
        self.total_row_count = total_rows
        self.current_row_count = 0
        self.report_def = report_def

    def add_rows(self, nb_rows: int):
        self.current_row_count += nb_rows

    def so_far(self) -> Tuple[float, int]:
        elapsed = time.time() - self.start_time
        rows_per_sec = int(self.current_row_count / elapsed)
        return elapsed, rows_per_sec

    def report(self, current):
        self.report_def(current, self.total_row_count)
