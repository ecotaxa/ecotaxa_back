# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import configparser
import random
import shutil
import zipfile
from pathlib import Path
# noinspection PyPackageRequirements
from typing import Callable, List, Dict, Tuple, Generator, Set

from BO.TSVFile import TSVFile
from BO.Taxonomy import TaxonomyBO
from BO.Vignette import VignetteMaker
from BO.helpers.ImportHelpers import ImportHow, ImportWhere, ImportDiagnostic, ImportStats
from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import ObjectHeader
from DB.Project import ProjectIDT
from DB.Sample import Sample
from DB.helpers import Session
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


class InBundle(object):
    """
        From EcoTaxa point of view, some structured data coming into the system.
        It contains TSV files and image files, in directory or directory tree.
        TSV files can be in a separate directory from image ones.
    """
    TSV_FILTERS = ("**/ecotaxa*.txt", "**/ecotaxa*.tsv")
    UVP6_FILTER = "**/*Images.zip"
    MAX_FILES = 1000

    def __init__(self, path: str, temp_dir: Path):
        self.path = Path(path)
        # Compute the files we have to process.
        self.possible_files: List[Path] = []
        nb_files = 0

        def one_more() -> None:
            nonlocal nb_files
            nb_files += 1
            if nb_files > self.MAX_FILES:
                raise ImportError("You tried to import too many files, max. is %d" % self.MAX_FILES)

        for a_filter in self.TSV_FILTERS:
            for a_file in self.path.glob(a_filter):
                self.possible_files.append(a_file)
                one_more()
        self.possible_files.sort()
        self.sub_bundles: List[UVP6Bundle] = []
        for a_bundle in self.path.glob(self.UVP6_FILTER):
            self.sub_bundles.append(UVP6Bundle(a_bundle, temp_dir))
            one_more()

    def possible_files_as_posix(self) -> Generator[str, None, None]:
        """
            Return the relative names of the files we have to process. Generator function.
        """
        for a_file in self.possible_files:
            relative_file = a_file.relative_to(self.path)
            # relative name for logging and recording what was done
            yield relative_file.as_posix()

    def do_import(self, where: ImportWhere, how: ImportHow, rowcount: int, report_def: Callable) -> int:
        """
            Import the full bundle, i.e. every contained file.
            :param where:
            :param how:
            :param rowcount: Total rowcount, from preparation step.
            :param report_def: A def to call at certain points for reporting progress.
            :return: The total number of rows
        """
        random.seed()
        stats = ImportStats(rowcount, report_def)
        # Borrow session from writer
        session = where.db_writer.session
        # Get structural parents, enclosing Sample and Acquisition
        how.existing_samples, how.existing_acquisitions = self.fetch_existing_parents(session, prj_id=how.prj_id)
        logger.info("existing samples = %s", list(how.existing_samples.keys()))
        logger.info("existing acquisitions = %s", list(how.existing_acquisitions.keys()))
        # The created objects (unicity from object_id in TSV, orig_id in model)
        how.existing_objects = self.fetch_existing_objects(session, prj_id=how.prj_id)
        # The stored images (unicity for object ID + rank)
        how.image_ranks_per_obj = self.fetch_existing_ranks(session, prj_id=how.prj_id)

        ret = self.import_each_file(where, how, stats)
        return ret

    def import_each_file(self, where: ImportWhere, how: ImportHow, stats: ImportStats) -> int:
        """
            Import each file in the bundle.
            :param where:
            :param how:
            :param stats:
        """

        def log_stats(name: str, rows: int) -> None:
            elapsed, rows_per_sec = stats.so_far()
            logger.info("File %s : %d rows loaded, %d so far at %d rows/s",
                        name, rows, stats.current_row_count,
                        rows_per_sec)

        for sub_bundle in self.sub_bundles:
            relative_name = sub_bundle.relative_name
            logger.info("Importing UVP6 file %s" % relative_name)
            sub_bundle.before_import(how)
            _rows_for_bundle = sub_bundle.import_each_file(where, how, stats)
            # Already counted in recursive call
            # stats.add_rows(rows_for_csv)
            sub_bundle.after_import(how)
            # Already displayed in recursive call
            # log_stats()

        for a_file in self.possible_files:
            tsv_to_read = TSVFile(a_file, self.path)
            relative_name = tsv_to_read.relative_name
            if relative_name in how.files_not_to_import:
                logger.info("Skipping load of already loaded file %s" % relative_name)
                continue
            else:
                logger.info("Importing file %s" % relative_name)
            rows_for_csv = tsv_to_read.do_import(where, how, stats)
            stats.add_rows(rows_for_csv)
            how.loaded_files.append(relative_name)
            where.db_writer.persist()
            log_stats(relative_name, rows_for_csv)

        where.db_writer.eof_cleanup()

        return stats.current_row_count

    @staticmethod
    def fetch_existing_objects(session: Session, prj_id: ProjectIDT) -> Dict[str, int]:
        """
            Get existing object IDs (orig_id AKA object_id in TSV) from the project
        """
        with CodeTimer("Existing objects for %d: " % prj_id, logger):
            return ObjectHeader.fetch_existing_objects(session, prj_id)

    @staticmethod
    def fetch_existing_ranks(session: Session, prj_id: ProjectIDT) -> Dict[int, Set[int]]:
        """
            Get existing image ranks from the project
        """
        return ObjectHeader.fetch_existing_ranks(session, prj_id)

    @staticmethod
    def fetch_existing_parents(session: Session, prj_id: ProjectIDT) \
            -> Tuple[Dict[str, Sample], Dict[Tuple[str, str], Acquisition]]:
        """
            Get from DB the present ORM instances for the tables we are going to update,
            in current project.
        """
        ret = (Sample.get_orig_id_and_model(session, prj_id),
               Acquisition.get_orig_id_and_model(session, prj_id))
        return ret

    def validate_import(self, how: ImportHow, diag: ImportDiagnostic, session: Session, report_def: Callable) -> int:
        """
            Validate the full bundle, i.e. every contained file.
            :return:
        """
        with CodeTimer("validate_import: Existing images for %d: " % how.prj_id, logger):
            how.objects_and_images_to_skip = Image.fetch_existing_images(session, how.prj_id)

        total_row_count = self.validate_each_file(how, diag, report_def)

        if total_row_count == 0:
            # Try to be explicit in messages
            nb_found = len(self.possible_files)
            nb_skipped = len(diag.skipped_files)
            err_msg = ["No object to import."]
            if nb_found == 0:
                err_msg.append("* No .txt or .tsv file was found, of which name starts with 'ecotaxa'.")
            else:
                nb_validated = nb_found - nb_skipped
                if nb_skipped > 0:
                    if nb_validated == 0:
                        err_msg.append("* 'SKIP TSV' option was set and all TSV files were imported before.")
                    else:
                        err_msg.append("* 'SKIP TSV' option was set and new TSV file(s) are not compliant.")
                if nb_validated > 0:
                    err_msg.append("*  TSV file(s) might be empty.")
                if how.skip_object_duplicates:
                    err_msg.append("*  'SKIP OBJECTS' option was set and all objects might be in already.")
            diag.error("<br>".join(err_msg))

        if len(diag.classif_id_seen) > 0:
            self.check_classif(session, diag, diag.classif_id_seen)

        logger.info("Taxo Found = %s", how.found_taxa)
        logger.info("Users Found = %s", how.found_users)
        not_seen_fields = how.custom_mapping.all_field_names() - diag.cols_seen
        if len(not_seen_fields) > 0:
            diag.warn("Some fields configured in the project are not seen in this import {0} "
                      .format(", ".join(not_seen_fields)))
        if diag.nb_objects_without_gps > 0:
            diag.warn("{0} object(s) don't have GPS information."
                      .format(diag.nb_objects_without_gps))
        return total_row_count

    def validate_each_file(self, how: ImportHow, diag: ImportDiagnostic, report_def: Callable) -> int:
        total_row_count = 0
        for num_file, sub_bundle in enumerate(self.sub_bundles):
            # It's another kind of bundle
            relative_name = sub_bundle.relative_name
            logger.info("Analyzing UVP6 %s" % relative_name)
            rows_for_csv = sub_bundle.validate_each_file(how, diag, report_def)

            logger.info("File %s : %d row analysed", relative_name, rows_for_csv)
            report_def(num_file, len(self.sub_bundles))
            total_row_count += rows_for_csv

        for num_file, a_file in enumerate(self.possible_files):
            # TSV file with attached images
            tsv_to_validate = TSVFile(a_file, self.path)
            relative_name = tsv_to_validate.relative_name
            if relative_name in how.files_not_to_import:
                logger.info("Skipping validation of already loaded file %s" % relative_name)
                diag.skipped_files.append(relative_name)
                continue
            else:
                logger.info("Analyzing file %s" % relative_name)
            report_def(num_file, len(self.possible_files))
            rows_for_csv = tsv_to_validate.do_validate(how, diag)

            logger.info("File %s : %d row analysed", relative_name, rows_for_csv)
            total_row_count += rows_for_csv

        return total_row_count

    @staticmethod
    def check_classif(session: Session, diag: ImportDiagnostic, classif_id_seen) -> None:
        classif_id_found_in_db = TaxonomyBO.find_ids(session, list(classif_id_seen))
        classif_id_not_found_in_db = classif_id_seen.difference(classif_id_found_in_db)
        if len(classif_id_not_found_in_db) > 0:
            msg = "Some specified classif_id don't exist, correct them prior to reload: %s" % \
                  (",".join([str(x) for x in classif_id_not_found_in_db]))
            diag.error(msg)
            logger.error(msg)

    def remove_all_tsvs(self) -> None:
        """
            Remove to-be-treated TSV files inside self,
            used in case a .zip with structured information is sent to Import Simple
        """
        self.possible_files = []

    def add_tsv(self, a_tsv_file: Path) -> None:
        """
            Add a TSV file for treatment.
        """
        self.possible_files.append(a_tsv_file)
        self.possible_files.sort()

    IMAGE_FILTERS = ("**/*.jpg", "**/*.png", "**/*.tif")

    def list_image_files(self) -> List[Path]:
        """
            Return the list of image files inside self, relative to self.
        """
        ret: List[Path] = []
        for a_filter in self.IMAGE_FILTERS:
            ret.extend(self.path.glob(a_filter))
        # Images are duplicated in a hidden folder for .zips coming from OsX
        ret = [a_file.relative_to(self.path)
               for a_file in ret
               if "__MACOSX" not in str(a_file)]
        return ret


class UVP6Bundle(InBundle):
    """
        An UVP6 bundle, i.e. an *Images.zip inside a enclosing .zip or directory.
        We have e.g. b_da_19_Images.zip.
        The zip contains:
            - At root, an optional vignette generation config (compute_vignette.txt)
            - At root, the index TSV file, with name derived from the zip, e.g. ecotaxa_b_da_19.tsv
    """
    VIGNETTE_CONFIG = "compute_vignette.txt"
    TEMP_VIGNETTE = "tempvignette.png"

    def __init__(self, path: Path, temp_dir: Path):
        assert path.suffix.lower() == ".zip"
        self.relative_name = path.name
        # Extract the zip file, in order to fall back to a directory like base InBundle
        name_no_zip = path.stem  # e.g. b_da_19_Images
        sample_id = name_no_zip[:-7]  # e.g. b_da_19
        # Derive directories & files
        # The file gets extracted into temporary directory, as .zip containing folder
        # might be write-protected
        sample_dir = temp_dir / name_no_zip
        tsv_file = "ecotaxa_" + sample_id + ".tsv"
        sample_tsv = sample_dir / tsv_file
        if sample_dir.exists():
            # Target directory exists, e.g. from step1 if we're in step2
            if not sample_tsv.exists():  # pragma: no cover
                # There was an incorrect unzipping before, as we miss the main TSV
                shutil.rmtree(sample_dir.as_posix())
        if not sample_dir.exists():
            sample_dir.mkdir()
            with zipfile.ZipFile(path.as_posix(), 'r') as z:
                z.extractall(sample_dir.as_posix())
        super().__init__(sample_dir.as_posix(), temp_dir)

    def before_import(self, how: ImportHow) -> None:
        how.vignette_maker = None
        # Pick vignette-ing config file from the zipped directory
        potential_config = self.path / self.VIGNETTE_CONFIG
        if potential_config.exists():
            vignette_maker_cfg = configparser.ConfigParser()
            vignette_maker_cfg.read(potential_config.as_posix())
            how.vignette_maker = VignetteMaker(vignette_maker_cfg, self.path, self.TEMP_VIGNETTE)

    @staticmethod
    def after_import(how: ImportHow) -> None:
        how.vignette_maker = None
