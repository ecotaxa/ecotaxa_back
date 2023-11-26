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

from API_models.exports import (
    ExportRsp,
    ExportReq,
    ExportTypeEnum,
    SummaryExportGroupingEnum,
)
from API_models.filters import ProjectFiltersDict
from BO.Mappings import ProjectMapping
from BO.ObjectSet import DescribedObjectSet
from BO.ObjectSetQueryPlus import ResultGrouping, IterableRowsT, ObjectSetQueryPlus
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO
from BO.Vocabulary import Vocabulary, Units
from DB.Object import (
    VALIDATED_CLASSIF_QUAL,
    DUBIOUS_CLASSIF_QUAL,
    PREDICTED_CLASSIF_QUAL,
)
from DB.Project import Project
from DB.helpers.Direct import text
from DB.helpers.SQL import OrderClause
from FS.CommonDir import ExportFolder
from FS.Vault import Vault
from helpers import (
    DateTime,
)  # Need to keep the whole module imported, as the function is mocked
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from ..helpers.JobService import JobServiceBase, ArgsDict

logger = get_logger(__name__)


class ProjectExport(JobServiceBase):
    """ """

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
        _user, _project = RightsBO.user_wants(
            self.session, current_user_id, Action.READ, self.req.project_id
        )
        # Security OK, create pending job
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = ExportRsp(job_id=self.job_id)
        return ret

    def init_args(self, args: ArgsDict) -> ArgsDict:
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
            if req.split_by == "sample" and "S" not in req.tsv_entities:
                req.tsv_entities += "S"
        # Bulk of the job
        if req.exp_type == ExportTypeEnum.general_tsv:
            nb_rows, _nb_images = self.create_tsv(src_project, progress_before_copy)
        elif req.exp_type in (ExportTypeEnum.backup, ExportTypeEnum.dig_obj_ident):
            nb_rows, nb_images = self.create_tsv(
                src_project, 10 if req.with_images else progress_before_copy
            )
            if req.with_images:
                self.add_images(nb_images, 10, progress_before_copy)
        elif req.exp_type == ExportTypeEnum.summary:
            nb_rows = self.create_summary(src_project)
        elif req.exp_type in (
            ExportTypeEnum.abundances,
            ExportTypeEnum.concentrations,
            ExportTypeEnum.biovols,
        ):
            nb_rows = self.create_sci_summary(src_project)
        else:
            raise Exception("Unsupported export type : %s" % req.exp_type)
        # Zip present log file as well
        if req.exp_type not in (
            ExportTypeEnum.summary,
            ExportTypeEnum.abundances,
            ExportTypeEnum.concentrations,
            ExportTypeEnum.biovols,
        ):
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
            final_message = (
                "Export successful : File '%s' is available (as well)"
                " in the 'Exported_data' FTP folder" % dest_name
            )
        else:
            final_message = "Export successful"

        self.update_progress(100, final_message)
        done_infos = {"rowcount": nb_rows, "out_file": self.out_file_name}
        self.set_job_result(errors=[], infos=done_infos)

    def append_log_to_zip(self) -> None:
        """
        Copy log file of present job into currently produced zip.
        """
        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(
            produced_path, "a", allowZip64=True, compression=zipfile.ZIP_DEFLATED
        )
        zfile.write(self.log_file_path(), arcname="job_%d.log" % self.job_id)
        zfile.close()

    def create_tsv(self, src_project: Project, end_progress: int) -> Tuple[int, int]:
        """
        Create the TSV file.
        """
        req = self.req
        proj_id = src_project.projid
        user_id = self._get_owner_id()
        self.update_progress(1, "Start TSV export")
        progress_range = end_progress - 1

        # Get a fast count of the maximum of what to do
        count_sql = "SELECT SUM(nbr) AS cnt FROM projects_taxo_stat WHERE projid = :prj"
        res = self.ro_session.execute(text(count_sql), {"prj": proj_id})
        obj_count = res.one()[0]

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.ro_session, src_project, user_id, self.filters
        )

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
            select_clause += (
                "img.orig_file_name AS img_file_name, img.imgrank AS img_rank"
            )
            if req.with_images:
                select_clause += ", img.file_name AS img_src_path"
            select_clause += ",\n"

        select_clause += (
            """obh.orig_id AS object_id, obh.latitude AS object_lat, obh.longitude AS object_lon,
                         TO_CHAR(obh.objdate,'{0}') AS object_date,
                         TO_CHAR(obh.objtime,'{1}') AS object_time,
                         obh.object_link, obh.depth_min AS object_depth_min, obh.depth_max AS object_depth_max,
                         CASE obh.classif_qual 
                            WHEN '"""
            + VALIDATED_CLASSIF_QUAL
            + """' then 'validated' 
                            WHEN '"""
            + PREDICTED_CLASSIF_QUAL
            + """' then 'predicted' 
                            WHEN '"""
            + DUBIOUS_CLASSIF_QUAL
            + """' then 'dubious' 
                            ELSE obh.classif_qual 
                         END AS object_annotation_status,                
                         usr.name AS object_annotation_person_name, usr.email AS object_annotation_person_email,
                         TO_CHAR(obh.classif_when,'{0}') AS object_annotation_date,
                         TO_CHAR(obh.classif_when,'{1}') AS object_annotation_time,                
                         txo.display_name AS object_annotation_category 
                    """
        ).format(date_fmt, time_fmt)
        if req.exp_type in (ExportTypeEnum.backup, ExportTypeEnum.dig_obj_ident):
            select_clause += ", txo.id AS object_annotation_category_id"
        else:
            # TODO: I didn't find where the below is used.
            select_clause += (
                ","
                + TaxonomyBO.parents_sql("obh.classif_id")
                + " AS object_annotation_hierarchy"
            )

        if "C" in req.tsv_entities:
            select_clause += "\n, obh.complement_info"

        # Deal with mappings, the goal is to emit SQL which will reconstitute the TSV structure
        src_mappings = ProjectMapping().load_from_project(src_project)
        if "O" in req.tsv_entities:
            select_clause += "\n " + src_mappings.object_mappings.as_select_list("obf")

        if "S" in req.tsv_entities:
            select_clause += "\n, sam.orig_id AS sample_id, sam.dataportal_descriptor AS sample_dataportal_descriptor "
            select_clause += src_mappings.sample_mappings.as_select_list("sam")

        if "P" in req.tsv_entities:
            select_clause += "\n, prc.orig_id AS process_id "
            select_clause += src_mappings.process_mappings.as_select_list("prc")

        if "A" in req.tsv_entities:
            select_clause += (
                "\n, acq.orig_id AS acq_id, acq.instrument AS acq_instrument "
            )
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
            if "S" in req.tsv_entities:
                select_clause += (
                    "\n, sam.latitude sample_lat, sam.longitude sample_long "
                )

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
        from_, where, params = object_set.get_sql(
            order_clause, select_clause, all_images=not req.only_first_image
        )
        sql = (
            select_clause
            + " FROM "
            + from_.get_sql()
            + where.get_sql()
            + order_clause.get_sql()
        )
        logger.info("Execute SQL : %s" % sql)
        logger.info("Params : %s" % params)

        res = self.ro_session.execute(text(sql), params)

        now_txt = DateTime.now_time().strftime("%Y%m%d_%H%M")
        self.out_file_name = "export_{0:d}_{1:s}.{2}".format(proj_id, now_txt, "zip")

        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(
            produced_path, "w", allowZip64=True, compression=zipfile.ZIP_DEFLATED
        )

        splitcsv = req.split_by != ""
        csv_filename = "data.tsv"  # Just a temp name as there is a renaming while filling up the Zip
        if splitcsv:
            # Produce into the same temp file all the time, at zipping time the name in archive will vary
            prev_value = "NotAssigned"  # To trigger a sequence change immediately
        else:
            # The zip will contain a single TSV with same base name as the zip
            prev_value = self.out_file_name.replace(".zip", "")

        csv_path: Path = (
            self.out_path / csv_filename
        )  # Constant path to a (sometimes) changing file
        csv_fd: Optional[TextIO] = None
        csv_wtr = None

        # Store the images to save in a separate CSV. Useless if not exporting images but who cares.
        temp_img_file = self.out_path / "images.csv"
        img_file_fd = open(temp_img_file, "w")
        img_wtr = csv.DictWriter(
            img_file_fd,
            ["src_path", "dst_path"],
            delimiter="\t",
            quotechar='"',
            lineterminator="\n",
        )
        img_wtr.writeheader()

        # Prepare TSV structure
        col_descs = [
            a_desc
            for a_desc in res.cursor.description  # type:ignore # case2
            if a_desc.name != "img_src_path"
        ]
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
        tsv_types_line = {
            name: ("[f]" if a_desc.type_code == db_float_type else "[t]")
            for name, a_desc in zip(tsv_cols, col_descs)
        }
        nb_rows = 0
        nb_images = 0
        used_dst_pathes = set()
        for r in res.mappings():
            # Rows from SQLAlchemy are not mutable, so we need a clone for arranging values
            a_row = dict(r)
            if (
                splitcsv and (prev_value != a_row[split_field])
            ) or (  # At each split column values change
                nb_rows == 0
            ):  # And anyway for the first row
                # Start of sequence, eventually end of previous sequence
                if csv_fd:
                    csv_fd.close()  # Close previous file
                    self.store_csv_into_zip(zfile, prev_value, csv_path)
                if splitcsv:
                    prev_value = a_row[split_field]
                logger.info("Writing into file %s", csv_path)
                if req.use_latin1:
                    csv_fd = open(csv_path, "w", encoding="latin_1")
                else:
                    csv_fd = open(csv_path, "w", encoding="utf-8-sig")
                csv_wtr = csv.DictWriter(
                    csv_fd,
                    tsv_cols,
                    delimiter="\t",
                    quotechar='"',
                    lineterminator="\n",
                    quoting=csv.QUOTE_NONNUMERIC,
                )
                csv_wtr.writeheader()
                if req.exp_type == ExportTypeEnum.backup:
                    # Write types line for backup type
                    csv_wtr.writerow(tsv_types_line)
            if req.with_images:
                copy_op = {"src_path": a_row.pop("img_src_path")}
                if req.exp_type == ExportTypeEnum.dig_obj_ident:
                    # Images will be stored in a per-category directory, but there is a single TSV at the Zip root
                    categ = a_row["object_annotation_category"]
                    categ_id: Optional[int] = a_row["object_annotation_category_id"]
                    # All names cannot directly become directories
                    a_row["img_file_name"] = self.get_DOI_imgfile_name(
                        a_row["objid"],
                        a_row["img_rank"],
                        categ,
                        categ_id,
                        a_row["img_file_name"],
                    )
                    copy_op["dst_path"] = a_row["img_file_name"]
                else:  # It's a backup
                    # Images are stored in the Zip subdirectory per sample/taxo, i.e. at the same place as
                    # their referring TSV
                    dst_path = "{0}/{1}".format(prev_value, a_row["img_file_name"])
                    if dst_path in used_dst_pathes:
                        # Avoid duplicates in zip as only the last entry will be present during unzip
                        # root cause: for UVP6 bundles, the vignette and original image are both stored
                        # with the same name.
                        img_with_rank = "{0}/{1}".format(
                            a_row["img_rank"], a_row["img_file_name"]
                        )
                        a_row[
                            "img_file_name"
                        ] = img_with_rank  # write into TSV the corrected path
                        dst_path = prev_value + "/" + img_with_rank
                    used_dst_pathes.add(dst_path)
                    copy_op["dst_path"] = dst_path
                img_wtr.writerow(copy_op)
                nb_images += 1
            # Remove CR from comments
            if "C" in req.tsv_entities and a_row["complement_info"]:
                a_row["complement_info"] = " ".join(
                    a_row["complement_info"].splitlines()
                )
            # Replace decimal separator
            for cname in float_cols:
                if a_row[cname] is not None:
                    a_row[cname] = str(a_row[cname]).replace(".", ",")
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

    def add_images(
        self, nb_files_to_add, start_progress: int, end_progress: int
    ) -> None:
        # Add image files, linked to the TSV content
        self.update_progress(start_progress, "Start Image export")
        progress_range = end_progress - start_progress
        logger.info("Appending to zip file %s" % self.out_file_name)
        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(
            produced_path, "a", allowZip64=True, compression=zipfile.ZIP_DEFLATED
        )

        nb_files_added = 0
        vault = Vault(self.config.vault_dir())
        temp_img_file = self.out_path / "images.csv"
        with open(temp_img_file, "r") as temp_images_csv_fd:
            for r in csv.DictReader(
                temp_images_csv_fd, delimiter="\t", quotechar='"', lineterminator="\n"
            ):
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
                    progress = int(
                        start_progress
                        + progress_range / nb_files_to_add * nb_files_added
                    )
                    self.update_progress(progress, msg)
            zfile.close()

    def get_DOI_imgfile_name(
        self,
        objid: int,
        imgrank: int,
        taxofolder: Optional[str],
        classif_id: Optional[int],
        originalfilename,
    ) -> str:
        if not taxofolder:
            taxofolder = "NoCategory"
        else:
            assert classif_id
            taxofolder += "__%d" % classif_id
        file_name = "images/{0}/{1}_{2}{3}".format(
            self.normalize_filename(taxofolder),
            objid,
            imgrank,
            Path(originalfilename).suffix.lower(),
        )
        return file_name

    @staticmethod
    def normalize_filename(filename) -> str:
        # noinspection RegExpRedundantEscape
        return re.sub(R"[^a-zA-Z0-9 \.\-\(\)]", "_", str(filename))

    def _get_summary_file(self, src_project):
        now_txt = DateTime.now_time().strftime("%Y%m%d_%H%M")
        self.out_file_name = "export_summary_{0:d}_{1:s}.tsv".format(
            src_project.projid, now_txt
        )
        out_file = self.temp_for_jobs.base_dir_for(self.job_id) / self.out_file_name
        return out_file

    def _grouping_from_req(self) -> ResultGrouping:
        req_sum = self.req.sum_subtotal
        if req_sum == SummaryExportGroupingEnum.just_by_taxon:
            return ResultGrouping.BY_TAXO
        elif req_sum == SummaryExportGroupingEnum.by_sample:
            return ResultGrouping.BY_SAMPLE_AND_TAXO
        elif req_sum == SummaryExportGroupingEnum.by_subsample:
            return ResultGrouping.BY_SAMPLE_SUBSAMPLE_AND_TAXO
        elif req_sum == SummaryExportGroupingEnum.by_project:
            assert False, "No collections yet to get multiple projects"
        else:
            assert False, "Incorrect required grouping : %s" % req_sum

    def create_summary(self, src_project: Project) -> int:
        req = self.req
        self.update_progress(1, "Start Summary export")

        out_file = self._get_summary_file(src_project)

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.ro_session, src_project, self._get_owner_id(), self.filters
        )

        # The specialized SQL builder
        aug_qry = ObjectSetQueryPlus(object_set)
        # We can set aliases even for expressions we don't select, so include all possibly needed ones
        aug_qry.set_aliases(
            {
                "sam.orig_id": "sample_id",
                "sam.latitude": "latitude",
                "sam.longitude": "longitude",
                "acq.orig_id": "acquis_id",
                "MAX(obh.objdate)": "date",
                "txo.display_name": "display_name",
                aug_qry.COUNT_STAR: "nbr",
            }
        )

        if req.sum_subtotal == SummaryExportGroupingEnum.just_by_taxon:
            pass
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_sample:
            aug_qry.add_selects(
                ["sam.orig_id", "sam.latitude", "sam.longitude", "MAX(obh.objdate)"]
            )
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_subsample:
            aug_qry.add_selects(["sam.orig_id", "acq.orig_id"])
        # We want the count, that's the goal of all this
        aug_qry.add_selects(["txo.display_name", aug_qry.COUNT_STAR])
        aug_qry.set_grouping(self._grouping_from_req())

        msg = "Writing to file %s" % out_file
        self.update_progress(50, msg)
        nb_lines = aug_qry.write_result_to_csv(
            self.ro_session, out_file, logger.warning
        )

        msg = "Extracted %d rows" % nb_lines
        logger.info(msg)
        self.update_progress(90, msg)

        return nb_lines

    def create_sci_abundances_summary(self, aug_qry: ObjectSetQueryPlus) -> str:
        """
        @see https://github.com/ecotaxa/ecotaxa/issues/615
        """
        self.update_progress(1, "Start Abundance Summary export")

        # We want count, in the end of the line
        aug_qry.set_aliases({aug_qry.COUNT_STAR: "count"})
        aug_qry.add_selects([aug_qry.COUNT_STAR])

        return "count"

    def create_sci_concentrations_summary(self, aug_qry: ObjectSetQueryPlus) -> str:
        """
        @see https://github.com/ecotaxa/ecotaxa/issues/616
        """
        self.update_progress(1, "Start Concentrations Summary export")

        # We want the sum of this formula calculation
        formula = "1/subsample_coef/total_water_volume"
        aug_qry.aggregate_with_computed_sum(
            formula, Vocabulary.concentrations, Units.number_per_cubic_metre
        )
        # Specific alias
        aug_qry.set_aliases({formula: "concentration"})

        return "concentration"

    def create_sci_biovolumes_summary(self, aug_qry: ObjectSetQueryPlus) -> str:
        """
        @see https://github.com/ecotaxa/ecotaxa/issues/617
        """
        self.update_progress(1, "Start Biovolumes Summary export")

        # We want the sum of formula calculation, for each object
        formula = "individual_volume/subsample_coef/total_water_volume"
        aug_qry.aggregate_with_computed_sum(
            formula, Vocabulary.biovolume, Units.cubic_millimetres_per_cubic_metre
        )
        # Specific alias
        aug_qry.set_aliases({formula: "biovolume"})

        return "biovolume"

    def add_zeroes_in_sci_summary(
        self, aug_qry: ObjectSetQueryPlus, id_cols: List[str], zero_col: str
    ):
        """
        Return relevant zero lines, for given non-zero input ones.
        param: id_cols: The identifying columns in the query.
        param: zero_col: The column to fill with 0 in the output.
        """
        if self.req.sum_subtotal in (
            SummaryExportGroupingEnum.by_sample,
            SummaryExportGroupingEnum.by_subsample,
        ):
            # Produce the zero-less report
            without_zeroes = aug_qry.get_result(self.ro_session, logger.warning)
            # Columns are aliased so the output columns are named differently
            out_id_cols = [aug_qry.defs_to_alias[a_col] for a_col in id_cols]
            not_presents = self.not_presents_in_sci_summary(
                without_zeroes, out_id_cols, zero_col, aug_qry.obj_set
            )
            without_zeroes.extend(not_presents)
            without_zeroes.sort(
                key=lambda a_row: tuple(
                    [a_row[id_col] for id_col in out_id_cols + ["taxonid"]]
                )
            )
            row_src: IterableRowsT = without_zeroes
        else:
            # We can write the query output
            row_src = aug_qry.get_row_source(self.ro_session, logger.warning)
        return row_src

    def not_presents_in_sci_summary(
        self,
        without_zeroes: List[Dict[str, Any]],
        id_cols: List[str],
        zero_col: str,
        object_set: DescribedObjectSet,
    ):
        """
        Produce lines with 0 abundance/concentration/biovolume for relevant (sample, category) pairs
        or (sample, acquisition, category) triplets.
        Specs: https://github.com/ecotaxa/ecotaxa/issues/615#issuecomment-1158781701
        """
        # Get all sampling_units (from the samples or subsamples AKA acquisition table)
        sampling_units_qry = (
            ObjectSetQueryPlus(object_set.without_filtering_taxo())
            .add_selects(self._id_columns_from_req())
            .set_aliases({"sam.orig_id": "sampleid", "acq.orig_id": "acquisid"})
            .set_grouping(ResultGrouping.without_taxo(self._grouping_from_req()))
        )
        all_sampling_units: Set[Tuple] = set()
        # Tuples here have either one or two values
        for a_row in sampling_units_qry.get_result(self.ro_session):
            all_sampling_units.add(tuple([a_row[id_col] for id_col in id_cols]))
        # Get possible taxa names
        txo_qry = (
            ObjectSetQueryPlus(object_set)
            .remap_categories(self.req.pre_mapping)
            .add_selects(["txo.display_name"])
            .set_aliases({"txo.display_name": "txo"})
            .set_grouping(ResultGrouping.BY_TAXO)
        )
        taxa: Set[str] = set(
            [a_row["txo"] for a_row in txo_qry.get_row_source(self.ro_session)]
        )
        # Prepare the cross fill, all with tuples which are hash-able
        presents: Set[Tuple[Tuple, str]] = set()
        # Build (sampling unit, taxon) pairs from zero-less report
        for a_row in without_zeroes:
            sampling_unit_id, taxonid = (
                tuple([a_row[id_col] for id_col in id_cols]),
                a_row["taxonid"],
            )
            presents.add((sampling_unit_id, taxonid))
        # Cross-fill
        not_presents: List[Dict[str, Any]] = []
        for sampling_unit_id in all_sampling_units:
            for taxonid in taxa:
                if (sampling_unit_id, taxonid) not in presents:
                    a_not_present = {
                        id_col: id_col_val
                        for id_col, id_col_val in zip(id_cols, sampling_unit_id)
                    }
                    a_not_present.update({"taxonid": taxonid, zero_col: 0})
                    not_presents.append(a_not_present)
        return not_presents

    def _id_columns_from_req(self):
        ret = []
        req = self.req
        if req.sum_subtotal == SummaryExportGroupingEnum.just_by_taxon:
            pass
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_sample:
            ret = ["sam.orig_id"]
        elif req.sum_subtotal == SummaryExportGroupingEnum.by_subsample:
            ret = ["sam.orig_id", "acq.orig_id"]
        return ret

    def create_sci_summary(self, src_project: Project) -> int:
        """
        Assuming that the historical summary is a data one, compute 'scientific' summaries.
        """
        req = self.req
        user_id = self._get_owner_id()
        exp_type = req.exp_type
        out_file = self._get_summary_file(src_project)

        # Ensure we work on validated objects only
        self.filters["statusfilter"] = "V"
        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.ro_session, src_project, user_id, self.filters
        )
        # The specialized SQL builder operates from the object set
        aug_qry = ObjectSetQueryPlus(object_set)
        aug_qry.remap_categories(req.pre_mapping)
        # Formulae default from the project but are overriden by the query
        formulae: Dict[str, str] = {}
        if src_project.variables is not None:
            formulae.update(src_project.variables.to_dict())
        formulae.update(req.formulae)
        aug_qry.set_formulae(formulae)
        # Set common aliases, not all of them is always used
        aug_qry.set_aliases(
            {
                "sam.orig_id": "sampleid",
                "acq.orig_id": "acquisid",
                "txo.display_name": "taxonid",
            }
        )
        id_cols = self._id_columns_from_req()
        aug_qry.add_selects(id_cols)
        aug_qry.add_selects(["txo.display_name"])

        if req.sum_subtotal == SummaryExportGroupingEnum.by_project:
            assert False, "No collections yet to get multiple projects from"

        # Per-type adjustment
        zero_col = ""
        if exp_type == ExportTypeEnum.abundances:
            zero_col = self.create_sci_abundances_summary(aug_qry)
        elif exp_type == ExportTypeEnum.concentrations:
            zero_col = self.create_sci_concentrations_summary(aug_qry)
        elif exp_type == ExportTypeEnum.biovols:
            zero_col = self.create_sci_biovolumes_summary(aug_qry)

        # Group according to request
        aug_qry.set_grouping(self._grouping_from_req())

        msg = "Computing zero lines to add"
        logger.info(msg)
        self.update_progress(30, msg)
        row_src = self.add_zeroes_in_sci_summary(aug_qry, id_cols, zero_col)

        msg = "Writing to file %s" % out_file
        logger.info(msg)
        self.update_progress(50, msg)
        nb_lines = aug_qry.write_row_source_to_csv(row_src, out_file)

        msg = "Extracted %d rows" % nb_lines
        logger.info(msg)
        self.update_progress(90, msg)

        return 0
