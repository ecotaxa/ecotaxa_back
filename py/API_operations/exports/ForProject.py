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
from os.path import join
from pathlib import Path
from typing import Dict, Optional, IO, Tuple

from API_models.crud import ProjectFilters
from API_models.exports import ExportRsp, ExportReq, ExportTypeEnum
from BO.Mappings import ProjectMapping
from BO.ObjectSet import DescribedObjectSet
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO
from DB.Project import Project
from DB.helpers.Direct import text
from DB.helpers.SQL import OrderClause
from FS.CommonDir import ExportFolder
from FS.Vault import Vault
from helpers import DateTime  # Need to keep the whole module imported, as the function is mocked
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from ..helpers.JobService import JobServiceBase

logger = get_logger(__name__)


class ProjectExport(JobServiceBase):
    """

    """
    JOB_TYPE = "GenExport"
    ROWS_REPORT_EVERY = 10000
    IMAGES_REPORT_EVERY = 1000

    def __init__(self, req: ExportReq, filters: ProjectFilters):
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

    def init_args(self, args: Dict) -> Dict:
        super().init_args(args)
        args["req"] = self.req.dict()
        args["filters"] = self.filters.__dict__
        return args

    @staticmethod
    def deser_args(json_args: Dict):
        json_args["req"] = ExportReq(**json_args["req"])
        json_args["filters"] = ProjectFilters(**json_args["filters"])  # type:ignore

    def do_background(self):
        """
            Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_export()

    @property
    def PRODUCED_FILE_NAME(self):
        return self.temp_for_jobs.search_base_dir_for(self.job_id, ".zip")

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
        else:
            raise Exception("Unsupported export type : %s" % req.exp_type)
        # Final copy
        if req.out_to_ftp:
            self.update_progress(progress_before_copy, "Copying file to FTP")
            dest = ExportFolder(self.config)
            # Disambiguate using the job ID
            dest_name = "task_%d_%s" % (self.job_id, self.out_file_name)
            dest.receive_from(self.out_path / self.out_file_name, dest_name)
            final_message = "Export successful : File '%s' is available (as well)" \
                            " in the 'Exported_data' FTP folder" % dest_name
        else:
            final_message = "Export successful"

        self.update_progress(100, final_message)
        self.set_job_result(errors=[], infos={"rowcount": nb_rows})

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
        obj_count = res.first()[0]

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
        select_clause = """select obh.orig_id AS object_id, obh.latitude AS object_lat, obh.longitude AS object_lon,
                         TO_CHAR(obh.objdate,'YYYYMMDD') AS object_date,
                         TO_CHAR(obh.objtime,'HH24MISS') AS object_time,
                         obh.object_link, obh.depth_min AS object_depth_min, obh.depth_max AS object_depth_max,
                         CASE obh.classif_qual 
                            WHEN 'V' then 'validated' 
                            WHEN 'P' then 'predicted' 
                            WHEN 'D' then 'dubious' 
                            ELSE obh.classif_qual 
                         END AS object_annotation_status,                
                         usr.name AS object_annotation_person_name, usr.email AS object_annotation_person_email,
                         TO_CHAR(obh.classif_when,'YYYYMMDD') AS object_annotation_date,
                         TO_CHAR(obh.classif_when,'HH24MISS') AS object_annotation_time,                
                         txo.display_name AS object_annotation_category 
                    """
        if req.exp_type == ExportTypeEnum.backup:
            select_clause += ", txo.id AS object_annotation_category_id"
        else:
            select_clause += "," + TaxonomyBO.parents_sql("obh.classif_id") + " AS object_annotation_hierarchy"

        if req.with_images:
            select_clause += "\n, img.orig_file_name AS img_file_name, img.imgrank AS img_rank, " \
                             "img.file_name AS img_src_path"

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
                    classif_auto_score, classif_auto_when,
                    obh.random_value object_random_value, obh.sunpos object_sunpos """
            if 'S' in req.tsv_entities:
                select_clause += "\n, sam.latitude sample_lat, sam.longitude sample_long "

        # TODO: The condition on o.projid=1 in historical code below prevents any data production
        # if 'H' in req.tsv_entities:
        #     sql1 += " , oh.classif_date AS histoclassif_date, classif_type AS histoclassif_type, " \
        #             "to3.name histoclassif_name, oh.classif_qual histoclassif_qual,uo3.name histoclassif_who, " \
        #             "classif_score histoclassif_score"
        #     sql2 += """ LEFT JOIN (select o.objid, classif_date, classif_type, och.classif_id,
        #                                   och.classif_qual, och.classif_who, classif_score
        #                              from objectsclassifhisto och
        #                              join objects o on o.objid=och.objid and o.projid=1 {0}
        #                            union all
        #                            select o.objid, o.classif_when classif_date, 'C' classif_type, classif_id,
        #                                   classif_qual, classif_who, NULL
        #                              from objects o {0} where o.projid=1
        #                           ) oh on o.objid=oh.objid
        #                 LEFT JOIN taxonomy to3 on oh.classif_id=to3.id
        #                 LEFT JOIN users uo3 on oh.classif_who=uo3.id
        #             """.format(samplefilter)

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

        if req.with_images:
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
        csv_fd: Optional[IO] = None
        csv_wtr = None

        # Store the images to save in a separate CSV. Useless if not exporting images but who cares.
        temp_img_file = self.out_path / "images.csv"
        img_file_fd = open(temp_img_file, 'w')
        img_wtr = csv.DictWriter(img_file_fd, ["src_path", "dst_path"],
                                 delimiter='\t', quotechar='"', lineterminator='\n')
        img_wtr.writeheader()

        # Prepare TSV structure
        col_descs = [a_desc for a_desc in res.cursor.description
                     if a_desc.name != "img_src_path"]
        # on lit le type de la colonne 2 alias latitude pour determiner le code du type double
        db_float_type = col_descs[2].type_code
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
                csv_fd = open(csv_path, 'w', encoding='latin_1')
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
                    # All names cannot directly become directories
                    categ = categ.replace("<", "_")
                    a_row['img_file_name'] = self.get_DOI_imgfile_name(a_row['objid'], a_row['img_rank'],
                                                                       categ, a_row['img_file_name'])
                    copy_op["dst_path"] = a_row['img_file_name']
                else:  # It's a backup
                    # Images are stored in the Zip subdirectory per sample/taxo, i.e. at the same place as
                    # their referring TSV
                    copy_op["dst_path"] = "{0}/{1}".format(prev_value, a_row['img_file_name'])
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

    def store_csv_into_zip(self, zfile, prev_value, in_file: Path):
        # Add a new file into the zip
        name_in_zip = "ecotaxa_" + str(prev_value) + ".tsv"
        if self.req.exp_type == ExportTypeEnum.backup:
            # In a subdirectory for backup type
            name_in_zip = str(prev_value) + os.sep + name_in_zip
        logger.info("Storing into zip as %s", name_in_zip)
        zfile.write(in_file, arcname=name_in_zip)

    def add_images(self, nb_files_to_add, start_progress: int, end_progress: int):
        # Add image files, linked to the TSV content
        self.update_progress(start_progress, "Start Image export")
        progress_range = end_progress - start_progress
        logger.info("Appending to zip file %s" % self.out_file_name)
        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(produced_path, 'a', allowZip64=True, compression=zipfile.ZIP_DEFLATED)

        nb_files_added = 0
        vault = Vault(join(self.link_src, 'vault'))
        temp_img_file = self.out_path / "images.csv"
        with open(temp_img_file, "r") as temp_images_csv_fd:
            for r in csv.DictReader(temp_images_csv_fd, delimiter='\t', quotechar='"', lineterminator='\n'):
                img_file_path = vault.path_to(r["src_path"])
                path_in_zip = r["dst_path"]
                try:
                    zfile.write(img_file_path, arcname=path_in_zip)
                except FileNotFoundError:
                    logger.error("Not found image: %s", path_in_zip)
                logger.info("Added file %s as %s", img_file_path, path_in_zip)
                nb_files_added += 1
                if nb_files_added % self.IMAGES_REPORT_EVERY == 0:
                    msg = "Added %d files" % nb_files_added
                    logger.info(msg)
                    progress = int(start_progress + progress_range / nb_files_to_add * nb_files_added)
                    self.update_progress(progress, msg)
            zfile.close()

    def get_DOI_imgfile_name(self, objid, imgrank, taxofolder, originalfilename):
        if not taxofolder:
            taxofolder = "NoCategory"
        file_name = "images/{0}/{1}_{2}{3}".format(self.normalize_filename(taxofolder),
                                                   objid, imgrank,
                                                   Path(originalfilename).suffix.lower())
        return file_name

    @staticmethod
    def normalize_filename(filename):
        # noinspection RegExpRedundantEscape
        return re.sub(R"[^a-zA-Z0-9 \.\-\(\)]", "_", str(filename))

    def create_summary(self, src_project: Project):
        self.update_progress(1, "Start Summary export")

        now_txt = DateTime.now_time().strftime("%Y%m%d_%H%M")
        self.out_file_name = "export_summary_{0:d}_{1:s}.tsv".format(src_project.projid, now_txt)
        out_file = self.temp_for_jobs.base_dir_for(self.job_id) / self.out_file_name

        grp = "to1.display_name"
        if self.req.sum_subtotal == "A":
            grp = "a.orig_id," + grp
        elif self.req.sum_subtotal == "S":
            grp = "s.orig_id, s.latitude, s.longitude," + grp

        sql1 = "SELECT " + grp
        if self.req.sum_subtotal == "S":
            # Il est demandé d'avoir la colonne agrégé date au milieu du groupe, donc réécriture de la requete.
            sql1 = "SELECT s.orig_id, s.latitude, s.longitude, MAX(objdate) AS date, to1.display_name"
        sql1 += ",COUNT(*) Nbr"
        sql2 = """ FROM objects o
                LEFT JOIN taxonomy to1 ON o.classif_id = to1.id
                     JOIN samples ON on o.sampleid = s.sampleid
                     JOIN acquisitions a ON o.acquisid = a.acquisid """
        sql3 = " WHERE o.projid = :projid "
        params = {'projid': self.req.project_id}

        # sql3 += sharedfilter.GetSQLFilter(self.param.filtres, params, self.task.owner_id)

        # Use the API entry point for filtering
        # with ApiClient(ObjectsApi, self.cookie) as api:
        #     res: ObjectSetQueryRsp = api.get_object_set_object_set_project_id_query_post(self.param.ProjectId,
        #                                                                                  self.param.filtres)
        #     sql3 += "and o.objid = any (%(objids)s) "
        #     params["objids"] = sorted(res.object_ids)

        sql3 += " group by " + grp
        sql3 += " order by " + grp

        sql = sql1 + " " + sql2 + " " + sql3
        logger.info("Execute SQL : %s" % (sql,))
        logger.info("Params : %s" % (params,))
        res = self.ro_session.execute(text(sql), params)

        msg = "Creating file %s" % out_file
        logger.info(msg)
        self.update_progress(50, msg)
        nb_lines = self.write_result_to_csv(res, out_file)
        msg = "Extracted %d rows" % nb_lines
        logger.info(msg)
        self.update_progress(90, msg)
        return nb_lines

    @staticmethod
    def write_result_to_csv(res, out_file):
        nb_lines = 0
        with open(out_file, 'w', encoding='latin_1') as csvfile:
            colnames = [desc[0] for desc in res.cursor.description]
            wtr = csv.DictWriter(csvfile, colnames, delimiter='\t', quotechar='"', lineterminator='\n')
            wtr.writerow({c: c for c in colnames})
            for r in res:
                a_row = {a_col: r[a_col] for a_col in colnames}
                wtr.writerow(a_row)
                nb_lines += 1
        return nb_lines
