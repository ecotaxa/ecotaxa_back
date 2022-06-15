# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Textual export of data. Presently TSV with images or not, XML.
#
import csv
import os
import re
import zipfile
from pathlib import Path
from typing import Optional, Tuple, TextIO, cast, Dict, List, Set, Any

from API_models.exports import ExportRsp, ExportReq, ExportTypeEnum, SummaryExportGroupingEnum
from API_models.filters import ProjectFiltersDict
from BO.Classification import ClassifIDT
from BO.Mappings import ProjectMapping
from BO.ObjectSet import DescribedObjectSet
from BO.ObjectSetQueryPlus import ResultGrouping, PerTaxonResultsQuery, IterableRowsT
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO
from BO.User import UserIDT
from DB.Object import VALIDATED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL, PREDICTED_CLASSIF_QUAL
from DB.Project import Project
from DB.helpers import Result
from DB.helpers.Direct import text
from DB.helpers.SQL import OrderClause
from FS.CommonDir import ExportFolder
from FS.Vault import Vault
from helpers import DateTime  # Need to keep the whole module imported, as the function is mocked
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from ..helpers.JobService import JobServiceBase, ArgsDict

logger = get_logger(__name__)


class ProjectExport(JobServiceBase):
    """

    """
    JOB_TYPE = "GenExport"
    ROWS_REPORT_EVERY = 10000
    IMAGES_REPORT_EVERY = 1000

    def __init__(self, req: ExportReq, filters: ProjectFiltersDict):
        super().__init__()
        self.req = req
        self.filters = filters
        self.out_file_name: str = ""
        self.out_path: Path = Path("")

    def run(self, current_user_id: int) -> ExportRsp:
        """
            Initial run, basically just do security check and create the job.
        """
        _user, _project = RightsBO.user_wants(self.session, current_user_id, Action.READ, self.req.project_id)
        # OK, go background straight away
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = ExportRsp(job_id=self.job_id)
        return ret

    def init_args(self, args: ArgsDict) -> ArgsDict:
        super().init_args(args)
        args["req"] = self.req.dict()
        args["filters"] = self.filters
        return args

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        json_args["req"] = ExportReq(**json_args["req"])
        json_args["filters"] = cast(ProjectFiltersDict, json_args["filters"])

    def do_background(self) -> None:
        """
            Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_export()

    # noinspection PyPep8Naming
    @property
    def PRODUCED_FILE_NAME(self) -> Optional[str]:
        result = self.get_job_result()
        if result is None:
            return None
        return result["out_file"]

    def do_export(self) -> None:
        """
            The real job.
        """
        self.out_path = self.temp_for_jobs.base_dir_for(self.job_id)
        req = self.req
        logger.info("Input Param = %s" % (self.req.__dict__,))
        # A bit of forward-thinking... Leave 5% of progress bar for final copy
        progress_before_copy = 100
        if req.out_to_ftp:
            progress_before_copy = 95
        # Fetch the source project
        src_project = self.ro_session.query(Project).get(req.project_id)
        assert src_project is not None
        # Force options for some types
        if req.exp_type in (ExportTypeEnum.backup, ExportTypeEnum.dig_obj_ident):
            req.tsv_entities = "OPAS"  # Not Comments nor History
            req.with_internal_ids = False
        if req.exp_type == ExportTypeEnum.backup:
            req.split_by = "sample"
            req.coma_as_separator = False
        elif req.exp_type == ExportTypeEnum.dig_obj_ident:
            req.split_by = ""
            req.coma_as_separator = False
        elif req.exp_type == ExportTypeEnum.general_tsv:
            req.with_images = False
            if req.split_by == "sample" and 'S' not in req.tsv_entities:
                req.tsv_entities += 'S'
        # Bulk of the job
        if req.exp_type == ExportTypeEnum.general_tsv:
            nb_rows, _nb_images = self.create_tsv(src_project, progress_before_copy)
        elif req.exp_type in (ExportTypeEnum.backup, ExportTypeEnum.dig_obj_ident):
            nb_rows, nb_images = self.create_tsv(src_project, 10 if req.with_images else progress_before_copy)
            if req.with_images:
                self.add_images(nb_images, 10, progress_before_copy)
        elif req.exp_type == ExportTypeEnum.summary:
            nb_rows = self.create_summary(src_project)
        elif req.exp_type in (ExportTypeEnum.abundances, ExportTypeEnum.concentrations, ExportTypeEnum.biovols):
            nb_rows = self.create_sci_summary(src_project)
        else:
            raise Exception("Unsupported export type : %s" % req.exp_type)
        # Zip present log file as well
        if req.exp_type not in (ExportTypeEnum.summary, ExportTypeEnum.abundances,
                                ExportTypeEnum.concentrations, ExportTypeEnum.biovols):
            logger.info("Log in zip should end here.")
            self.append_log_to_zip()
        # Final copy
        if req.out_to_ftp:
            self.update_progress(progress_before_copy, "Copying file to FTP")
            dest = ExportFolder(self.config.export_folder())
            # Disambiguate using the job ID
            dest_name = "task_%d_%s" % (self.job_id, self.out_file_name)
            dest.receive_from(self.out_path / self.out_file_name, dest_name)
            logger.info("Result copied to %s", dest_name)
            final_message = "Export successful : File '%s' is available (as well)" \
                            " in the 'Exported_data' FTP folder" % dest_name
        else:
            final_message = "Export successful"

        self.update_progress(100, final_message)
        done_infos = {"rowcount": nb_rows,
                      "out_file": self.out_file_name}
        self.set_job_result(errors=[], infos=done_infos)

    def append_log_to_zip(self) -> None:
        """
            Copy log file of present job into currently produced zip.
        """
        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(produced_path, 'a', allowZip64=True, compression=zipfile.ZIP_DEFLATED)
        zfile.write(self.log_file_path(), arcname="job_%d.log" % self.job_id)
        zfile.close()

    def create_tsv(self, src_project: Project, end_progress: int) -> Tuple[int, int]:
        """
            Create the TSV file.
        """
        req = self.req
        proj_id = src_project.projid
        self.update_progress(1, "Start TSV export")
        progress_range = end_progress - 1

        # Get a fast count of the maximum of what to do
        count_sql = "SELECT SUM(nbr) AS cnt FROM projects_taxo_stat WHERE projid = :prj"
        res = self.ro_session.execute(text(count_sql), {"prj": proj_id})
        obj_count = res.one()[0]

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.ro_session, proj_id, self.filters)

        # Backup or not, the column namings are taken from common mapping
        # @See Mapping.py
        # TSV column order
        # field_order = ["object_id", "object_lat", "object_lon", "object_date", "object_time", "object_depth_max",
        #                "object_annotation_status", "object_annotation_person_name", "object_annotation_person_email",
        #                "object_annotation_date", "object_annotation_time", "object_annotation_category"]
        # formats = {"object_date": "TO_CHAR({0},'YYYYMMDD')",
        #            "object_time": "TO_CHAR({0},'HH24MISS')",
        #            "object_annotation_date": "TO_CHAR({0},'YYYYMMDD')",
        #            "object_annotation_time": "TO_CHAR({0},'HH24MISS')",
        #            "object_annotation_status": """
        #                  CASE {0}
        #                     WHEN 'V' then 'validated'
        #                     WHEN 'P' then 'predicted'
        #                     WHEN 'D' then 'dubious'
        #                     ELSE {0}
        #                  END
        #            """
        #            }
        # prefices = {ObjectHeader.__tablename__: "obh",
        #             }
        # for a_fld in field_order:
        #     mpg = GlobalMapping.PREDEFINED_FIELDS[a_fld]
        #     mpg[""]
        #     assert a_fld in GlobalMapping.PREDEFINED_FIELDS, "%s is not a mapped column" % a_fld
        date_fmt, time_fmt = "YYYYMMDD", "HH24MISS"
        if req.format_dates_times and not (req.exp_type == ExportTypeEnum.backup):
            # Do not make nice dates for backup
            date_fmt, time_fmt = "YYYY-MM-DD", "HH24:MI:SS"

        select_clause = "select "

        if req.with_images or (req.exp_type == ExportTypeEnum.backup):
            select_clause += "img.orig_file_name AS img_file_name, img.imgrank AS img_rank"
            if req.with_images:
                select_clause += ", img.file_name AS img_src_path"
            select_clause += ",\n"

        select_clause += ("""obh.orig_id AS object_id, obh.latitude AS object_lat, obh.longitude AS object_lon,
                         TO_CHAR(obh.objdate,'{0}') AS object_date,
                         TO_CHAR(obh.objtime,'{1}') AS object_time,
                         obh.object_link, obh.depth_min AS object_depth_min, obh.depth_max AS object_depth_max,
                         CASE obh.classif_qual 
                            WHEN '""" + VALIDATED_CLASSIF_QUAL + """' then 'validated' 
                            WHEN '""" + PREDICTED_CLASSIF_QUAL + """' then 'predicted' 
                            WHEN '""" + DUBIOUS_CLASSIF_QUAL + """' then 'dubious' 
                            ELSE obh.classif_qual 
                         END AS object_annotation_status,                
                         usr.name AS object_annotation_person_name, usr.email AS object_annotation_person_email,
                         TO_CHAR(obh.classif_when,'{0}') AS object_annotation_date,
                         TO_CHAR(obh.classif_when,'{1}') AS object_annotation_time,                
                         txo.display_name AS object_annotation_category 
                    """).format(date_fmt, time_fmt)
        if req.exp_type in (ExportTypeEnum.backup, ExportTypeEnum.dig_obj_ident):
            select_clause += ", txo.id AS object_annotation_category_id"
        else:
            # TODO: I didn't find where the below is used.
            select_clause += "," + TaxonomyBO.parents_sql("obh.classif_id") + " AS object_annotation_hierarchy"

        if 'C' in req.tsv_entities:
            select_clause += "\n, obh.complement_info"

        # Deal with mappings, the goal is to emit SQL which will reconstitute the TSV structure
        src_mappings = ProjectMapping().load_from_project(src_project)
        if 'O' in req.tsv_entities:
            select_clause += "\n " + src_mappings.object_mappings.as_select_list("obf")

        if 'S' in req.tsv_entities:
            select_clause += "\n, sam.orig_id AS sample_id, sam.dataportal_descriptor AS sample_dataportal_descriptor "
            select_clause += src_mappings.sample_mappings.as_select_list("sam")

        if 'P' in req.tsv_entities:
            select_clause += "\n, prc.orig_id AS process_id "
            select_clause += src_mappings.process_mappings.as_select_list("prc")

        if 'A' in req.tsv_entities:
            select_clause += "\n, acq.orig_id AS acq_id, acq.instrument AS acq_instrument "
            select_clause += src_mappings.acquisition_mappings.as_select_list("acq")

        if req.exp_type == ExportTypeEnum.dig_obj_ident:
            select_clause += "\n, obh.objid"

        if req.with_internal_ids:
            select_clause += """\n, obh.objid, 
                    obh.acquisid AS processid_internal, obh.acquisid AS acq_id_internal, 
                    sam.sampleid AS sample_id_internal, 
                    obh.classif_id, obh.classif_who, obh.classif_auto_id, txp.name classif_auto_name, 
                    obh.classif_auto_score, obh.classif_auto_when,
                    obh.random_value object_random_value, obh.sunpos object_sunpos """
            if 'S' in req.tsv_entities:
                select_clause += "\n, sam.latitude sample_lat, sam.longitude sample_long "

        order_clause = OrderClause()
        if req.split_by == "sample":
            order_clause.add_expression("sam", "orig_id")
            split_field = "sample_id"  # AKA sam.orig_id, but renamed in select list
        elif req.split_by == "taxo":
            select_clause += "\n, txo.display_name AS taxo_parent_child "
            order_clause.add_expression(None, "taxo_parent_child")
            split_field = "taxo_parent_child"
        else:
            order_clause.add_expression("sam", "orig_id")
            split_field = "object_id"  # cette valeur permet d'éviter des erreurs plus loin dans r[split_field]
        order_clause.add_expression("obh", "objid")

        if req.with_images or (req.exp_type == ExportTypeEnum.backup):
            order_clause.add_expression(None, "img_rank")

        # Base SQL comes from filters
        from_, where, params = object_set.get_sql(self._get_owner_id(), order_clause, select_clause,
                                                  all_images=not req.only_first_image)
        sql = select_clause + " FROM " + from_.get_sql() + where.get_sql() + order_clause.get_sql()
        logger.info("Execute SQL : %s" % sql)
        logger.info("Params : %s" % params)

        res = self.ro_session.execute(text(sql), params)

        now_txt = DateTime.now_time().strftime("%Y%m%d_%H%M")
        self.out_file_name = "export_{0:d}_{1:s}.{2}".format(proj_id, now_txt, "zip")

        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(produced_path, 'w', allowZip64=True, compression=zipfile.ZIP_DEFLATED)

        splitcsv = (req.split_by != "")
        csv_filename = 'data.tsv'  # Just a temp name as there is a rename while filling up the Zip
        if splitcsv:
            # Produce into the same temp file all the time, at zipping time the name in archive will vary
            prev_value = "NotAssigned"  # To trigger a sequence change immediately
        else:
            # The zip will contain a single TSV with same base name as the zip
            prev_value = self.out_file_name.replace('.zip', '')

        csv_path: Path = self.out_path / csv_filename  # Constant path to a (sometimes) changing file
        csv_fd: Optional[TextIO] = None
        csv_wtr = None

        # Store the images to save in a separate CSV. Useless if not exporting images but who cares.
        temp_img_file = self.out_path / "images.csv"
        img_file_fd = open(temp_img_file, 'w')
        img_wtr = csv.DictWriter(img_file_fd, ["src_path", "dst_path"],
                                 delimiter='\t', quotechar='"', lineterminator='\n')
        img_wtr.writeheader()

        # Prepare TSV structure
        col_descs = [a_desc for a_desc in res.cursor.description  # type:ignore # case2
                     if a_desc.name != "img_src_path"]
        # read latitude column to get float DB type
        for a_desc in col_descs:
            if a_desc.name == "object_lat":
                db_float_type = a_desc.type_code
                break
        else:
            raise
        float_cols = set()
        # Prepare float separator conversion, if not required the set will just be empty
        if req.coma_as_separator:
            for a_desc in col_descs:
                if a_desc.type_code == db_float_type:
                    float_cols.add(a_desc.name)

        tsv_cols = [a_desc.name for a_desc in col_descs]
        tsv_types_line = {name: ('[f]' if a_desc.type_code == db_float_type else '[t]')
                          for name, a_desc in zip(tsv_cols, col_descs)}
        nb_rows = 0
        nb_images = 0
        used_dst_pathes = set()
        for r in res:
            # Rows from SQLAlchemy are not mutable, so we need a clone for arranging values
            a_row = dict(r)
            if ((splitcsv and (prev_value != a_row[split_field]))  # At each split column values change
                    or (nb_rows == 0)):  # And anyway for the first row
                # Start of sequence, eventually end of previous sequence
                if csv_fd:
                    csv_fd.close()  # Close previous file
                    self.store_csv_into_zip(zfile, prev_value, csv_path)
                if splitcsv:
                    prev_value = a_row[split_field]
                logger.info("Writing into file %s", csv_path)
                if req.use_latin1:
                    csv_fd = open(csv_path, 'w', encoding='latin_1')
                else:
                    csv_fd = open(csv_path, 'w', encoding='utf-8-sig')
                csv_wtr = csv.DictWriter(csv_fd, tsv_cols,
                                         delimiter='\t', quotechar='"', lineterminator='\n',
                                         quoting=csv.QUOTE_NONNUMERIC)
                csv_wtr.writeheader()
                if req.exp_type == ExportTypeEnum.backup:
                    # Write types line for backup type
                    csv_wtr.writerow(tsv_types_line)
            if req.with_images:
                copy_op = {"src_path": a_row.pop("img_src_path")}
                if req.exp_type == ExportTypeEnum.dig_obj_ident:
                    # Images will be stored in a per-category directory, but there is a single TSV at the Zip root
                    categ = a_row['object_annotation_category']
                    categ_id: Optional[int] = a_row['object_annotation_category_id']  # type:ignore
                    # All names cannot directly become directories
                    a_row['img_file_name'] = self.get_DOI_imgfile_name(a_row['objid'], a_row['img_rank'],
                                                                       categ, categ_id, a_row['img_file_name'])
                    copy_op["dst_path"] = a_row['img_file_name']
                else:  # It's a backup
                    # Images are stored in the Zip subdirectory per sample/taxo, i.e. at the same place as
                    # their referring TSV
                    dst_path = "{0}/{1}".format(prev_value, a_row['img_file_name'])
                    if dst_path in used_dst_pathes:
                        # Avoid duplicates in zip as only the last entry will be present during unzip
                        # root cause: for UVP6 bundles, the vignette and original image are both stored
                        # with the same name.
                        img_with_rank = "{0}/{1}".format(a_row['img_rank'], a_row['img_file_name'])
                        a_row['img_file_name'] = img_with_rank  # write into TSV the corrected path
                        dst_path = prev_value + "/" + img_with_rank
                    used_dst_pathes.add(dst_path)
                    copy_op["dst_path"] = dst_path
                img_wtr.writerow(copy_op)
                nb_images += 1
            # Remove CR from comments
            if 'C' in req.tsv_entities and a_row['complement_info']:
                a_row['complement_info'] = ' '.join(a_row['complement_info'].splitlines())
            # Replace decimal separator
            for cname in float_cols:
                if a_row[cname] is not None:
                    a_row[cname] = str(a_row[cname]).replace('.', ',')
            assert csv_wtr is not None
            # Produce the row in the TSV
            csv_wtr.writerow(a_row)
            nb_rows += 1
            if nb_rows % self.ROWS_REPORT_EVERY == 0:
                msg = "Row %d of max %d" % (nb_rows, obj_count)
                logger.info(msg)
                self.update_progress(1 + progress_range / obj_count * nb_rows, msg)
        if csv_fd:
            csv_fd.close()  # Close last file
            self.store_csv_into_zip(zfile, prev_value, csv_path)
        logger.info("Extracted %d rows", nb_rows)
        img_file_fd.close()
        if zfile:
            zfile.close()
        return nb_rows, nb_images

    def store_csv_into_zip(self, zfile, prev_value, in_file: Path) -> None:
        # Add a new file into the zip
        name_in_zip = "ecotaxa_" + str(prev_value) + ".tsv"
        if self.req.exp_type == ExportTypeEnum.backup:
            # In a subdirectory for backup type
            name_in_zip = str(prev_value) + os.sep + name_in_zip
        logger.info("Storing into zip as %s", name_in_zip)
        zfile.write(in_file, arcname=name_in_zip)

    def add_images(self, nb_files_to_add, start_progress: int, end_progress: int) -> None:
        # Add image files, linked to the TSV content
        self.update_progress(start_progress, "Start Image export")
        progress_range = end_progress - start_progress
        logger.info("Appending to zip file %s" % self.out_file_name)
        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(produced_path, 'a', allowZip64=True, compression=zipfile.ZIP_DEFLATED)

        nb_files_added = 0
        vault = Vault(self.config.vault_dir())
        temp_img_file = self.out_path / "images.csv"
        with open(temp_img_file, "r") as temp_images_csv_fd:
            for r in csv.DictReader(temp_images_csv_fd, delimiter='\t', quotechar='"', lineterminator='\n'):
                img_file_path = vault.image_path(r["src_path"])
                path_in_zip = r["dst_path"]
                try:
                    zfile.write(img_file_path, arcname=path_in_zip)
                except FileNotFoundError:
                    logger.error("Not found image: %s", img_file_path)
                    continue
                logger.info("Added file %s as %s", img_file_path, path_in_zip)
                nb_files_added += 1
                if nb_files_added % self.IMAGES_REPORT_EVERY == 0:
                    msg = "Added %d files" % nb_files_added
                    logger.info(msg)
                    progress = int(start_progress + progress_range / nb_files_to_add * nb_files_added)
                    self.update_progress(progress, msg)
            zfile.close()

    def get_DOI_imgfile_name(self, objid: int, imgrank: int, taxofolder: Optional[str], classif_id: Optional[int],
                             originalfilename) -> str:
        if not taxofolder:
            taxofolder = "NoCategory"
        else:
            assert classif_id
            taxofolder += "__%d" % classif_id
        file_name = "images/{0}/{1}_{2}{3}".format(self.normalize_filename(taxofolder),
                                                   objid, imgrank,
                                                   Path(originalfilename).suffix.lower())
        return file_name

    @staticmethod
    def normalize_filename(filename) -> str:
        # noinspection RegExpRedundantEscape
        return re.sub(R"[^a-zA-Z0-9 \.\-\(\)]", "_", str(filename))

    def _get_summary_file(self, src_project):
        now_txt = DateTime.now_time().strftime("%Y%m%d_%H%M")
        self.out_file_name = "export_summary_{0:d}_{1:s}.tsv".format(src_project.projid, now_txt)
        out_file = self.temp_for_jobs.base_dir_for(self.job_id) / self.out_file_name
        return out_file

    def create_summary(self, src_project: Project) -> int:
        req = self.req
        proj_id = src_project.projid
        self.update_progress(1, "Start Summary export")

        out_file = self._get_summary_file(src_project)

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.ro_session, proj_id, self.filters)

        # The specialized SQL builder
        aug_qry: PerTaxonResultsQuery = PerTaxonResultsQuery(object_set, self._get_owner_id(), "txo.display_name")
        # We want the count, that's the goal of all this
        aug_qry.aggregate_with_count()
        # We can set aliases even for expressions we don't select, so include all possibly needed ones
        aug_qry.set_aliases({"sam.orig_id": "sample_id",
                             "sam.latitude": "latitude",
                             "sam.longitude": "longitude",
                             "acq.orig_id": "acquis_id",
                             "MAX(obh.objdate)": "date",
                             "txo.display_name": "display_name",
                             aug_qry.COUNT_STAR: "nbr"})

        if req.sum_subtotal == SummaryExportGroupingEnum.just_by_taxon:
            pass  # Default value
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_sample:
            aug_qry.add_select(["sam.orig_id", "sam.latitude", "sam.longitude", "MAX(obh.objdate)"]). \
                set_grouping(ResultGrouping.BY_SAMPLE_AND_TAXO)
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_subsample:
            aug_qry.add_select(["sam.orig_id", "acq.orig_id"]). \
                set_grouping(ResultGrouping.BY_SUBSAMPLE_AND_TAXO)
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_project:
            assert False, "No collections yet to get multiple projects"

        msg = "Writing to file %s" % out_file
        self.update_progress(50, msg)
        nb_lines = aug_qry.write_result_to_csv(self.ro_session, out_file)

        msg = "Extracted %d rows" % nb_lines
        logger.info(msg)
        self.update_progress(90, msg)

        return nb_lines

    def create_sci_abundances_summary(self, src_project: Project) -> int:
        """
            @see https://github.com/ecotaxa/ecotaxa/issues/615
        """
        req = self.req
        proj_id = src_project.projid
        user_id = self._get_owner_id()
        self.update_progress(1, "Start Abundance Summary export")

        out_file = self._get_summary_file(src_project)

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.ro_session, proj_id, self.filters)

        # The specialized SQL builder
        aug_qry: PerTaxonResultsQuery = PerTaxonResultsQuery(object_set, user_id, "txo.display_name")
        aug_qry.remap_categories(req.pre_mapping)
        aug_qry.set_formulae(req.formulae)
        # We want the count, that's the goal of all this
        aug_qry.aggregate_with_count()
        # We can set aliases even for expressions we don't select, so include all possibly needed ones
        aug_qry.set_aliases({"txo.display_name": "taxonid",
                             "sam.orig_id": "sampleid",
                             "acq.orig_id": "acquisid",
                             aug_qry.COUNT_STAR: "count"})

        if req.sum_subtotal == SummaryExportGroupingEnum.just_by_taxon:
            aug_qry.set_grouping(ResultGrouping.BY_TAXO)
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_sample:
            aug_qry.add_select(["sam.orig_id"]). \
                set_grouping(ResultGrouping.BY_SAMPLE_AND_TAXO)
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_subsample:
            aug_qry.add_select(["sam.orig_id", "acq.orig_id"]). \
                set_grouping(ResultGrouping.BY_SUBSAMPLE_AND_TAXO)

        if req.sum_subtotal == SummaryExportGroupingEnum.by_sample:
            # We need to add missing taxa
            without_zeroes = aug_qry.get_result(self.ro_session)
            not_presents = self.add_not_presents_in_summary(without_zeroes, object_set, user_id, "count")
            without_zeroes.extend(not_presents)
            without_zeroes.sort(key=lambda row: (row["sampleid"], row["taxonid"]))
            row_src: IterableRowsT = without_zeroes
        else:
            # We can write the query output
            row_src = aug_qry.get_row_source(self.ro_session)

        msg = "Writing to file %s" % out_file
        self.update_progress(50, msg)
        nb_lines = aug_qry.write_row_source_to_csv(row_src, out_file)

        msg = "Extracted %d rows" % nb_lines
        logger.info(msg)
        self.update_progress(90, msg)

        return nb_lines

    def add_not_presents_in_summary(self, without_zeroes: List[Dict[str, Any]], object_set: DescribedObjectSet,
                                    user_id: UserIDT, zero_col: str):
        """
            Add lines with 0 abundance/concentration/biovolume for relevant (sample, category) pairs.
        """
        presents: Set[Tuple[str, str]] = set()
        samples: Set[str] = set()
        taxa: Set[str] = set()
        # Build (sample, taxon) pairs
        for a_row in without_zeroes:
            sampleid, taxonid = a_row["sampleid"], a_row["taxonid"]
            presents.add((sampleid, taxonid))
            samples.add(sampleid)
            taxa.add(taxonid)
        # We want as well all the samples implied by the filters
        # TODO: Put the query somewhere else
        from_, where_clause, params = object_set.get_sql(user_id)
        sql = "SELECT DISTINCT sam.orig_id FROM " + from_.get_sql() + " " + where_clause.get_sql()
        res: Result = self.ro_session.execute(text(sql), params)
        for sampleid, in res:
            samples.add(sampleid)
        # Cross-fill
        not_presents: List[Dict[str, Any]] = []
        for sampleid in samples:
            for taxonid in taxa:
                if (sampleid, taxonid) not in presents:
                    not_presents.append({"sampleid": sampleid,
                                         "taxonid": taxonid,
                                         zero_col: 0})
        return not_presents

    def create_sci_concentrations_summary(self, src_project: Project) -> int:
        """
            @see https://github.com/ecotaxa/ecotaxa/issues/616
        """
        req = self.req
        proj_id = src_project.projid
        user_id = self._get_owner_id()
        self.update_progress(1, "Start Concentrations Summary export")

        out_file = self._get_summary_file(src_project)

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.ro_session, proj_id, self.filters)

        # The specialized SQL builder
        aug_qry: PerTaxonResultsQuery = PerTaxonResultsQuery(object_set, user_id, "txo.display_name")
        aug_qry.remap_categories(req.pre_mapping)
        aug_qry.set_formulae(req.formulae)
        # We want the sum of formula calculation
        formula = "1/SubSamplingCoefficient/VolWBodySamp"
        aug_qry.aggregate_with_computed_sum(formula)
        # We can set aliases even for expressions we don't select, so include all possibly needed ones
        aug_qry.set_aliases({"txo.display_name": "taxonid",
                             "sam.orig_id": "sampleid",
                             "acq.orig_id": "acquisid",
                             formula: "concentration"})

        if req.sum_subtotal == SummaryExportGroupingEnum.just_by_taxon:
            aug_qry.set_grouping(ResultGrouping.BY_TAXO)
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_sample:
            aug_qry.add_select(["sam.orig_id"]). \
                set_grouping(ResultGrouping.BY_SAMPLE_AND_TAXO)
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_subsample:
            aug_qry.add_select(["sam.orig_id", "acq.orig_id"]). \
                set_grouping(ResultGrouping.BY_SUBSAMPLE_AND_TAXO)

        if req.sum_subtotal == SummaryExportGroupingEnum.by_sample:
            # We need to add missing taxa
            without_zeroes = aug_qry.get_result(self.ro_session)
            not_presents = self.add_not_presents_in_summary(without_zeroes, object_set, user_id, "concentration")
            without_zeroes.extend(not_presents)
            without_zeroes.sort(key=lambda row: (row["sampleid"], row["taxonid"]))
            row_src: IterableRowsT = without_zeroes
        else:
            # We can write the query output
            row_src = aug_qry.get_row_source(self.ro_session)

        msg = "Writing to file %s" % out_file
        self.update_progress(50, msg)
        nb_lines = aug_qry.write_row_source_to_csv(row_src, out_file)

        msg = "Extracted %d rows" % nb_lines
        logger.info(msg)
        self.update_progress(90, msg)

        return nb_lines

    def create_sci_summary(self, src_project: Project) -> int:
        """
            Assuming that the historical summary is a data one, compute 'scientific' summaries.
        """
        req = self.req
        exp_type = req.exp_type

        # Ensure we work on validated obejcts only
        self.filters["statusfilter"] = "V"

        # TODO: Get and apply category mapping from Req
        categ_mapping: Optional[Dict[ClassifIDT, ClassifIDT]] = None

        if req.sum_subtotal == SummaryExportGroupingEnum.by_project:
            assert False, "No collections yet to get multiple projects"

        if exp_type == ExportTypeEnum.abundances:
            return self.create_sci_abundances_summary(src_project)
        elif exp_type == ExportTypeEnum.concentrations:
            return self.create_sci_concentrations_summary(src_project)
        elif exp_type == ExportTypeEnum.biovols:
            raise Exception("Not implemented biovolume summary report")

        # msg = "Produced %d rows" % nb_lines
        # logger.info(msg)
        # self.update_progress(90, msg)
        return 0
