# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import configparser
import logging
import random
import shutil
import time
import zipfile
from pathlib import Path

# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from BO.Mappings import GlobalMapping
from BO.TSVFile import TSVFile
from BO.Vignette import VignetteMaker
from BO.helpers.ImportHelpers import ImportHow, ImportWhere, ImportDiagnostic
from db.Image import Image
from db.Object import Object
from db.Taxonomy import Taxonomy

logger = logging.getLogger(__name__)


class InBundle(object):
    """
        From EcoTaxa point of view, some structured data coming into the system.
    """
    FILTERS = ("**/ecotaxa*.txt", "**/ecotaxa*.tsv", "**/*Images.zip")

    def __init__(self, path: str):
        self.path = Path(path)
        # Compute the files we have to process.
        self.possible_files = []
        for a_filter in self.FILTERS:
            self.possible_files.extend(self.path.glob(a_filter))

    def possible_files_as_posix(self):
        """
            Return the relative names of the files we have to process. Generator function.
        """
        for a_file in self.possible_files:
            relative_file = a_file.relative_to(self.path)
            # relative name for logging and recording what was done
            yield relative_file.as_posix()

    def do_import(self, where: ImportWhere, how: ImportHow) -> int:
        """
            Import the full bundle, i.e. every contained file.
            :param where:
            :param how:
            :return:
        """
        random.seed()
        total_row_count = 0
        start_time = time.time()
        # Borrow session from writer
        session = where.db_writer.session
        # Get parent (enclosing) Sample, Acquisition, Process, if any
        how.existing_parent_ids = self.fetch_existing_parent_ids(session, prj_id=how.prj_id)
        # The created objects (unicity from object_id in TSV, orig_id in model)
        how.existing_objects = self.fetch_existing_objects(session, prj_id=how.prj_id)
        logger.info("existing_parent_ids = %s", how.existing_parent_ids)

        ret = self.import_each_file(where, how, start_time, total_row_count)
        return ret

    def import_each_file(self, where: ImportWhere, how: ImportHow, start_time, total_row_count):
        """
            Import each file in the bundle.
            :param where:
            :param how:
            :param start_time:
            :param total_row_count:
            :return:
        """

        for a_file in self.possible_files:

            if a_file.name.endswith("Images.zip"):
                # It's another kind of bundle
                sub_bundle = UVPV6Bundle(a_file)
                relative_name = sub_bundle.relative_name
                logger.info("Importing UVPV6 file %s" % relative_name)
                sub_bundle.before_import(how)
                rows_for_csv = sub_bundle.import_each_file(where, how, start_time, total_row_count)
                sub_bundle.after_import(how)
            else:
                tsv_to_read = TSVFile(a_file, self.path)
                relative_name = tsv_to_read.relative_name
                logger.info("Importing file %s" % relative_name)
                if relative_name in how.files_not_to_import:
                    continue

                rows_for_csv = tsv_to_read.do_import(where, how,
                                                     total_row_count, self.notify_user)

                how.loaded_files.append(relative_name)

                where.db_writer.persist()

            elapsed = time.time() - start_time
            rows_per_sec = int(total_row_count / elapsed)
            logger.info("File %s : %d rows loaded, %d so far at %d rows/s",
                        relative_name, rows_for_csv, total_row_count,
                        rows_per_sec)

        where.db_writer.eof_cleanup()

        return total_row_count

    def notify_user(self, count):
        """
            Callback during TSV import.
        """
        # TODO
        # self.UpdateProgress(100 * total_row_count / self.param.TotalRowCount,
        #                     "Processing files %d/%d" % (total_row_count, self.total_row_count))

    @staticmethod
    def fetch_existing_objects(session, prj_id):
        """
            Get existing object IDs (orig_id AKA object_id in TSV) from the project
        """
        return Object.fetch_existing_objects(session, prj_id)

    @staticmethod
    def fetch_existing_parent_ids(session, prj_id):
        """
            Get from DB the present IDs for the tables we are going to update, in current project.
            :return:
        """
        existing_ids = {}
        # Get orig_id from acquisition, sample, process
        for alias, clazz in GlobalMapping.parent_classes.items():
            collect = clazz.get_orig_id_and_pk(session, prj_id)
            existing_ids[alias] = collect
        return existing_ids

    def validate_import(self, session: Session, how: ImportHow, diag: ImportDiagnostic):
        """
            Validate the full bundle, i.e. every contained file.
            :return:
        """
        how.objects_and_images_to_skip = Image.fetch_existing_images(session, how.prj_id)

        total_row_count = self.validate_all_files(how, diag, session)

        if total_row_count == 0:
            diag.error("No object to import. It maybe due to :<br>"
                       "*  Empty TSV table<br>"
                       "*  TSV table already imported => 'SKIP TSV' option should be enabled")
        # print(self.mapping)
        if len(diag.classif_id_seen) > 0:
            self.check_classif(session, diag, diag.classif_id_seen)

        logger.info("Taxo Found = %s", how.taxo_found)
        logger.info("Users Found = %s", how.found_users)
        not_seen_fields = how.custom_mapping.all_fields.keys() - diag.cols_seen
        logger.info("For Information, not seen fields %s", not_seen_fields)
        if len(not_seen_fields) > 0:
            diag.warn("Some fields configured in the project are not seen in this import {0} "
                      .format(", ".join(not_seen_fields)))
        if diag.nb_objects_without_gps > 0:
            diag.warn("{0} object(s) don't have GPS information."
                      .format(diag.nb_objects_without_gps))
        return total_row_count

    def validate_all_files(self, how, diag, session):

        total_row_count = 0
        for a_file in self.possible_files:

            if a_file.name.endswith("Images.zip"):
                # It's another kind of bundle
                sub_bundle = UVPV6Bundle(a_file)
                relative_name = sub_bundle.relative_name
                logger.info("Analyzing UVPV6 %s" % relative_name)
                rows_for_csv = sub_bundle.validate_all_files(how, diag, session)
                sub_bundle.cleanup()
            else:
                tsv_to_validate = TSVFile(a_file, self.path)
                relative_name = tsv_to_validate.relative_name
                logger.info("Analyzing file %s" % relative_name)
                if relative_name in how.files_not_to_import:
                    continue
                rows_for_csv = tsv_to_validate.do_validate(how, diag)

            logger.info("File %s : %d row analysed", relative_name, rows_for_csv)
            total_row_count += rows_for_csv

        return total_row_count

    @staticmethod
    def check_classif(session: Session, diag: ImportDiagnostic, classif_id_seen):
        classif_id_found_in_db = Taxonomy.find_ids(session, list(classif_id_seen))
        classif_id_not_found_in_db = classif_id_seen.difference(classif_id_found_in_db)
        if len(classif_id_not_found_in_db) > 0:
            msg = "Some specified classif_id don't exist, correct them prior to reload: %s" % \
                  (",".join([str(x) for x in classif_id_not_found_in_db]))
            diag.error(msg)
            logger.error(msg)


class UVPV6Bundle(InBundle):
    """
        An UVPV6 bundle, i.e. an *Images.zip inside a enclosing .zip or directory.
        We have e.g. b_da_19_Images.zip.
        The zip contains:
            - At root, an optional vignette generation config (compute_vignette.txt)
            - At root, the index TSV file, with name derived from the zip, e.g. ecotaxa_b_da_19.tsv
    """
    VIGNETTE_CONFIG = "compute_vignette.txt"
    TEMP_VIGNETTE = "tempvignette.png"

    def __init__(self, path: Path):
        assert path.suffix.lower() == ".zip"
        self.relative_name = path.name
        # Extract the zip file, in order to fall back to a directory like base InBundle
        name_no_zip = path.stem  # e.g. b_da_19_Images
        sample_id = name_no_zip[:-7]  # e.g. b_da_19
        # Derive directories & files
        # The file gets extracted by convention in same directory as its parent
        sample_dir = path.parent / name_no_zip
        tsv_file = "ecotaxa_" + sample_id + ".tsv"
        sample_tsv = sample_dir / tsv_file
        if sample_dir.exists():
            # Target directory exists, from step1 if we're in step2
            if not sample_tsv.exists():
                # There was an incorrect unzipping before, as we miss the main TSV
                shutil.rmtree(sample_dir.as_posix())
        if not sample_dir.exists():
            sample_dir.mkdir()
            with zipfile.ZipFile(path.as_posix(), 'r') as z:
                z.extractall(sample_dir.as_posix())
        super().__init__(sample_dir.as_posix())

    def before_import(self, how: ImportHow):
        how.vignette_maker = None
        # Pick vignette-ing config file from the zipped directory
        potential_config = self.path / self.VIGNETTE_CONFIG
        if potential_config.exists():
            vignette_maker_cfg = configparser.ConfigParser()
            vignette_maker_cfg.read(potential_config.as_posix())
            how.vignette_maker = VignetteMaker(vignette_maker_cfg, self.path, self.TEMP_VIGNETTE)

    @staticmethod
    def after_import(how: ImportHow):
        how.vignette_maker = None

    def cleanup(self):
        shutil.rmtree(self.path)
