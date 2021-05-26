# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Textual export of data. Presently TSV with images or not, XML.
#
import csv
import datetime
import os
import re
import zipfile
from os.path import join
from pathlib import Path
from typing import Dict

from API_models.crud import ProjectFilters
from API_models.exports import ExportRsp, ExportReq, ExportTypeEnum
from BO.Mappings import ProjectMapping
from BO.Rights import RightsBO, Action
from DB.Project import Project
from DB.helpers.Direct import text
from FS.CommonDir import ExportFolder
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from ..helpers.JobService import JobServiceBase

logger = get_logger(__name__)


class ProjectExport(JobServiceBase):
    """

    """
    JOB_TYPE = "GenExport"

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
        elif req.exp_type == ExportTypeEnum.dig_obj_ident:
            req.split_by = ""
        # Bulk of the job
        if req.exp_type == ExportTypeEnum.general_tsv:
            nb_rows = self.create_tsv(src_project, progress_before_copy)
        elif req.exp_type == ExportTypeEnum.backup:
            nb_rows = self.create_tsv(src_project, 10 if req.with_images else progress_before_copy)
            if req.with_images:
                self.add_images('sample', 10, progress_before_copy)
        elif req.exp_type == ExportTypeEnum.dig_obj_ident:
            nb_rows = self.create_tsv(src_project, 10 if req.with_images else progress_before_copy)
            if req.with_images:
                self.add_images('taxo', 10, progress_before_copy)
        elif req.exp_type == ExportTypeEnum.summary:
            nb_rows = self.create_summary(src_project)
        else:
            raise Exception("Unsupported exportation type : %s" % (req.exp_type,))
        # Final copy
        if req.out_to_ftp:
            self.update_progress(progress_before_copy, "Copying file to FTP")
            dest = ExportFolder(self.config)
            # Disambiguate using the job ID
            dest_name = "task_%d_%s" % (self.job_id, self.out_file_name)
            dest.receive_from(self.out_path, self.out_file_name)
            self.out_file_name = ''
            final_message = "Export successful : File '%s' is available on the 'Exported_data' FTP folder" % dest_name
        else:
            final_message = "Export successful"

        self.update_progress(100, final_message)
        self.set_job_result(errors=[], infos={"rowcount": nb_rows})

    def create_tsv(self, src_project: Project, end_progress: int) -> int:
        """
            Create the TSV file.
        """
        req = self.req
        prj_id = src_project.projid
        self.update_progress(1, "Start TSV export")
        progress_range = end_progress - 1

        # Get a fast count of the maximum of what to do
        count_sql = "SELECT SUM(nbr) AS cnt FROM projects_taxo_stat WHERE projid = :prj"
        res = self.ro_session.execute(text(count_sql), {"prj": prj_id})
        obj_count = res.first()[0]

        # Backup or not, the column namings are taken from common mapping
        sql1 = """select o.orig_id AS object_id, o.latitude AS object_lat, o.longitude AS object_lon,
                         to_char(o.objdate,'YYYYMMDD') AS object_date,
                         to_char(o.objtime,'HH24MISS') AS object_time,
                         o.object_link, o.depth_min AS object_depth_min, o.depth_max AS object_depth_max,
                         case o.classif_qual 
                            when 'V' then 'validated' 
                            when 'P' then 'predicted' 
                            when 'D' then 'dubious' 
                            else o.classif_qual 
                         end AS object_annotation_status,                
                         uo1.name AS object_annotation_person_name, uo1.email AS object_annotation_person_email,
                         to_char(o.classif_when,'YYYYMMDD') AS object_annotation_date,
                         to_char(o.classif_when,'HH24MISS') AS object_annotation_time,                
                         to1.display_name AS object_annotation_category 
                    """
        if req.exp_type == ExportTypeEnum.backup:
            sql1 += ",to1.id AS object_annotation_category_id"
        else:
            sql1 += """
                ,(WITH RECURSIVE rq(id,name,parent_id) 
                   AS (SELECT id, name, parent_id, 1 rang 
                         FROM taxonomy 
                        WHERE id = o.classif_id
                       union
                       select t.id, t.name, t.parent_id, rang+1 rang 
                         from rq 
                         join taxonomy t on t.id = rq.parent_id)
                    select string_agg(name,'>') 
                      from (select name 
                              from rq 
                              order by rang desc) q) object_annotation_hierarchy """

        sql2 = """ FROM objects o
                LEFT JOIN taxonomy to1 ON o.classif_id = to1.id
                LEFT JOIN taxonomy to1p ON to1.parent_id = to1p.id
                LEFT JOIN users uo1 ON o.classif_who = uo1.id
                LEFT JOIN taxonomy to2 ON o.classif_auto_id = to2.id
                     JOIN samples s ON o.sampleid = s.sampleid """

        sql3 = " WHERE o.projid = :projid "

        params = {'projid': src_project.projid}

        if req.with_images:  # First image
            sql1 += "\n,img.orig_file_name AS img_file_name, img.imgrank AS img_rank"
            if req.only_first_image:
                sql2 += "\nleft join images img on o.objid = img.objid " \
                        "                      and img.imgrank = (SELECT MIN(img2.imgrank) " \
                        "                                           FROM images img2 WHERE img2.objid = o.objid) "
            else:
                sql2 += "\nleft join images img on o.objid = img.objid "

        if 'C' in req.tsv_entities:
            sql1 += "\n,complement_info"

        def no_special_char(col):
            # noinspection RegExpRedundantEscape
            return re.sub(R"[^a-zA-Z0-9\.\-µ]", "_", col)

        original_col_name = {}  # Nom de colonne SQL => Nom de colonne permet de traiter le cas de %area
        # Deal with mappings, the goal is to emit SQL which will reconstitute the TSV structure
        src_mappings = ProjectMapping().load_from_project(src_project)
        if 'O' in req.tsv_entities:
            sql1 += "\n"
            mapping = src_mappings.object_mappings
            for k, v in mapping.real_cols_to_tsv.items():
                alias_sql = 'object_%s' % no_special_char(v)
                original_col_name[alias_sql] = 'object_%s' % v
                sql1 += ',o.%s as "%s" ' % (k, alias_sql)

        if 'S' in req.tsv_entities:
            sql1 += "\n,s.orig_id AS sample_id, s.dataportal_descriptor AS sample_dataportal_descriptor "
            mapping = src_mappings.sample_mappings
            for k, v in mapping.real_cols_to_tsv.items():
                sql1 += ',s.%s AS "sample_%s" ' % (k, no_special_char(v))

        if 'P' in req.tsv_entities:
            sql1 += "\n,p.orig_id process_id"
            mapping = src_mappings.process_mappings
            for k, v in mapping.real_cols_to_tsv.items():
                sql1 += ',p.%s AS "process_%s" ' % (k, no_special_char(v))
            sql2 += " JOIN process p ON o.acquisid = p.processid "

        if 'A' in req.tsv_entities:
            sql1 += "\n,a.orig_id AS acq_id,a.instrument AS acq_instrument"
            mapping = src_mappings.acquisition_mappings
            for k, v in mapping.real_cols_to_tsv.items():
                sql1 += ',a.%s AS "acq_%s" ' % (k, no_special_char(v))
            sql2 += " JOIN acquisitions a ON o.acquisid = a.acquisid "

        if req.exp_type == ExportTypeEnum.dig_obj_ident:
            sql1 += "\n,o.objid"

        if req.with_internal_ids:
            sql1 += """\n,o.objid, 
                    o.acquisid AS acq_id_internal, o.acquisid AS processid_internal, o.sampleid AS sample_id_internal, 
                    o.classif_id, o.classif_who,
                    o.classif_auto_id, to2.name classif_auto_name, classif_auto_score, classif_auto_when,
                    o.random_value object_random_value, o.sunpos object_sunpos """
            if 'S' in req.tsv_entities:
                sql1 += "\n, s.latitude sample_lat, s.longitude sample_long "

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

        # Use the API entry point for filtering
        # with ApiClient(ObjectsApi, self.cookie) as api:
        #     res: ObjectSetQueryRsp = api.get_object_set_object_set_project_id_query_post(self.param.ProjectId,
        #                                                                                  self.param.filtres)
        #     sql3 += "and o.objid = any (%(objids)s) "
        #     params["objids"] = sorted(res.object_ids)

        if req.split_by == "sample":
            sql3 += " ORDER BY s.orig_id, o.objid "
            split_field = "sample_id"  # AKA s.orig_id, but renamed in select list
        elif req.split_by == "taxo":
            sql1 += "\n,concat(to1p.name,'_',to1.name) taxo_parent_child "
            sql3 += " ORDER BY taxo_parent_child, o.objid "
            split_field = "taxo_parent_child"
        else:
            sql3 += " ORDER BY s.orig_id, o.objid "  # tri par defaut
            split_field = "object_id"  # cette valeur permet d'éviter des erreurs plus loin dans r[split_field]

        if req.with_images:
            sql3 += ",img_rank"

        sql = sql1 + " " + sql2 + " " + sql3
        logger.info("Execute SQL : %s" % (sql,))
        logger.info("Params : %s" % (params,))

        res = self.ro_session.execute(text(sql), params)
        now_txt = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.out_file_name = "export_{0:d}_{1:s}.{2}".format(prj_id, now_txt, "zip")

        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(produced_path, 'w', allowZip64=True, compression=zipfile.ZIP_DEFLATED)

        splitcsv = (req.split_by != "")
        if splitcsv:
            csvfilename = 'temp.tsv'
            prev_value = "NotAssigned"
        else:
            csvfilename = self.out_file_name.replace('.zip', '.tsv')
            prev_value = self.out_file_name.replace('.zip', '')

        curr_file = self.out_path / csvfilename
        csvfile = None
        wtr = None

        colnames = [desc.name for desc in res.cursor.description]
        coltypes = [desc.type_code for desc in res.cursor.description]
        # on lit le type de la colonne 2 alias latitude pour determiner le code du type double
        db_float_type = coltypes[2]
        nb_rows = 0
        for r in res:
            # Rows from SQLAlchemy are not mutable, so we need a clone for arranging values
            a_row = {a_col: r[a_col] for a_col in colnames}
            if (csvfile is None and (not splitcsv)) or \
                    ((prev_value != a_row[split_field]) and splitcsv):
                if csvfile:
                    self.close_csv_if_needed(req.exp_type, csvfile, curr_file, zfile, prev_value)
                if splitcsv:
                    prev_value = a_row[split_field]
                logger.info("Creating file %s" % curr_file)
                csvfile = open(curr_file, 'w', encoding='latin_1')
                wtr = csv.DictWriter(csvfile, [original_col_name.get(c, c) for c in colnames],
                                     delimiter='\t', quotechar='"', lineterminator='\n',
                                     quoting=csv.QUOTE_NONNUMERIC)
                # Write header line
                wtr.writerow({n: n for n in colnames})
                if req.exp_type == ExportTypeEnum.backup:
                    # Write type lines for backup type
                    wtr.writerow({n: ('[f]' if t == db_float_type else '[t]')
                                  for n, t in zip(colnames, coltypes)})
            if 'img_file_name' in a_row and req.exp_type == ExportTypeEnum.dig_obj_ident:
                # les images sont dans des dossiers par taxo
                a_row['img_file_name'] = self.get_DOI_imgfile_name(a_row['objid'], a_row['img_rank'],
                                                                   a_row['object_annotation_category'],
                                                                   a_row['img_file_name'])
            # Remove CR from comments
            if 'C' in req.tsv_entities and a_row['complement_info']:
                a_row['complement_info'] = ' '.join(a_row['complement_info'].splitlines())
            # Replace decimal separator
            if req.coma_as_separator:
                for cname, ctype in zip(colnames, coltypes):
                    if ctype == db_float_type and a_row[cname] is not None:
                        a_row[cname] = str(a_row[cname]).replace('.', ',')
            logger.info("writing %s", a_row)
            assert wtr is not None
            wtr.writerow(a_row)
            nb_rows += 1
            if nb_rows % 10000 == 0:
                msg = "Row %d of max %d" % (nb_rows, obj_count)
                logger.info(msg)
                self.update_progress(1 + progress_range / obj_count * nb_rows, msg)
        if csvfile:
            self.close_csv_if_needed(req.exp_type, csvfile, curr_file, zfile, prev_value)
        logger.info("Extracted %d rows", nb_rows)
        if zfile:
            zfile.close()
        return nb_rows

    @staticmethod
    def close_csv_if_needed(export_type, csv_file, in_file, zfile, prev_value):
        csv_file.close()
        if not zfile:
            return
        # Adding a new file into the zip
        name_in_zip = "ecotaxa_" + str(prev_value) + ".tsv"
        if export_type == ExportTypeEnum.backup:
            # In a subdirectory for backup type
            name_in_zip = str(prev_value) + os.sep + name_in_zip
        zfile.write(in_file, arcname=name_in_zip)

    def add_images(self, split_image_by: str, start_progress: int, end_progress: int):

        self.update_progress(start_progress, "Start Image export")
        progress_range = end_progress - start_progress
        logger.info("Opening (for append) file %s" % self.out_file_name)
        produced_path = self.out_path / self.out_file_name
        zfile = zipfile.ZipFile(produced_path, 'a', allowZip64=True, compression=zipfile.ZIP_DEFLATED)

        sql = """select i.objid, i.file_name, i.orig_file_name, t.name, 
                        replace(t.display_name,'<','_') taxo_parent_child, imgrank,
                        s.orig_id sample_orig_id
                   from objects o 
                        join samples s on o.sampleid = s.sampleid
                   join images i on o.objid = i.objid
                   left join taxonomy t on o.classif_id = t.id
                   left join taxonomy to1p on t.parent_id = to1p.id
                  where o.projid = :projid """
        params = {'projid': self.req.project_id}

        # sql += sharedfilter.GetSQLFilter(self.param.filtres, params, self.task.owner_id)

        # # Use the API entry point for filtering
        # with ApiClient(ObjectsApi, self.cookie) as api:
        #     res: ObjectSetQueryRsp = api.get_object_set_object_set_project_id_query_post(self.param.ProjectId,
        #                                                                                  self.param.filtres)
        #     sql += "and o.objid = any (%(objids)s) "
        #     params["objids"] = sorted(res.object_ids)

        logger.info("Execute SQL : %s" % sql)
        logger.info("Params : %s" % params)

        res = self.ro_session.execute(text(sql), params)
        temp_img_file = self.temp_for_jobs.base_dir_for(self.job_id) / "images.csv"
        # Write the resultset to a file in order to free cursor data ecotaxa/ecotaxa_dev#542
        nb_files_to_add = self.write_result_to_csv(res, temp_img_file)
        nb_files_added = 0
        vault = Vault(join(self.link_src, 'vault'))
        with open(temp_img_file, "r") as temp_images_csv_fd:
            for r in csv.DictReader(temp_images_csv_fd, delimiter='\t', quotechar='"', lineterminator='\n'):
                img_file_path = vault.path_to(r["file_name"])
                if split_image_by == 'taxo':
                    path_in_zip = self.get_DOI_imgfile_name(r['objid'], r['imgrank'],
                                                            r['taxo_parent_child'], r['file_name'])
                else:
                    path_in_zip = "{0}/{1}".format(r['sample_orig_id'], r['orig_file_name'])
                try:
                    zfile.write(img_file_path, arcname=path_in_zip)
                except FileNotFoundError:
                    logger.error("Not found image: %s", path_in_zip)
                logger.info("Added file %s as %s", img_file_path, path_in_zip)
                nb_files_added += 1
                if nb_files_added % 1000 == 0:
                    msg = "Added %d files" % nb_files_added
                    logger.info(msg)
                    progress = int(start_progress + progress_range / nb_files_to_add * nb_files_added)
                    self.update_progress(progress, msg)
            zfile.close()

    def get_DOI_imgfile_name(self, objid, imgrank, taxofolder, originalfilename):
        if not taxofolder:
            taxofolder = "NoCategory"
        file_name = "images/{0}/{1}_{2}{3}".format(self.normalize_filename(taxofolder), objid, imgrank,
                                                   Path(originalfilename).suffix.lower())
        return file_name

    @staticmethod
    def normalize_filename(filename):
        # noinspection RegExpRedundantEscape
        return re.sub(R"[^a-zA-Z0-9 \.\-\(\)]", "_", str(filename))

    def create_summary(self, src_project: Project):
        self.update_progress(1, "Start Summary export")

        now_txt = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.out_file_name = "export_summary_{0:d}_{1:s}.tsv".format(src_project.projid, now_txt)
        out_file = self.temp_for_jobs.base_dir_for(self.job_id) / self.out_file_name

        grp = "to1.display_name"
        if self.req.sum_subtotal == "A":
            grp = "a.orig_id," + grp
        elif self.req.sum_subtotal == "S":
            grp = "s.orig_id,s.latitude,s.longitude," + grp

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
