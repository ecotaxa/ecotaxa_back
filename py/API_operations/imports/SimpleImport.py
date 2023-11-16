# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

from API_models.imports import SimpleImportReq, SimpleImportRsp, SimpleImportFields
from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
from BO.helpers.ImportHelpers import ImportWhere, ImportHow
from DB.Object import ObjectHeader, classif_qual
from DB.helpers.DBWriter import DBWriter
from helpers.DynamicLogs import get_logger, LogsSwitcher
from .ImportBase import ImportServiceBase
from ..helpers.JobService import ArgsDict

logger = get_logger(__name__)


class SimpleImport(ImportServiceBase):
    """
    Simple import, i.e. many images with same metadata.
    """

    req: SimpleImportReq  # Not used, just for typings
    JOB_TYPE = "SimpleImport"

    def __init__(self, prj_id: int, req: SimpleImportReq, dry_run: bool):
        super().__init__(prj_id, req)
        self.dry_run = dry_run

    def init_args(self, args: ArgsDict) -> ArgsDict:
        super().init_args(args)
        args["dry_run"] = False
        return args

    @staticmethod
    def deser_args(json_args: ArgsDict) -> None:
        json_args["req"] = SimpleImportReq(**json_args["req"])

    def run(self, current_user_id: int) -> SimpleImportRsp:
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.ANNOTATE, self.prj_id)
        # Validate values in all cases, dry run or not.
        ret = self._validate()
        if len(ret.errors) > 0:
            return ret
        if not self.dry_run:
            # Security OK, create pending job
            self.create_job(self.JOB_TYPE, current_user_id)
            ret.job_id = self.job_id
        return ret

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_import()

    def do_import(self) -> None:
        """
        Do the real job, i.e. copy files while creating records. Runs in background.
        """
        errors: List[str] = []
        source_dir_or_zip = self.unzip_if_needed(self._get_owner_id())
        # Use a Bundle
        source_bundle = InBundle(
            source_dir_or_zip, Path(self.temp_for_jobs.data_dir_for(self.job_id))
        )
        # Clean it, in case the ZIP contains a CSV
        source_bundle.remove_all_tsvs()
        images = source_bundle.list_image_files()
        # Configure the import to come, destination
        db_writer = DBWriter(self.session)
        import_where = ImportWhere(
            db_writer, self.vault, self.temp_for_jobs.base_dir_for(self.job_id)
        )
        # Configure the import to come, directives
        import_how = ImportHow(
            prj_id=self.prj_id,
            update_mode="",
            custom_mapping=ProjectMapping(),
            skip_object_duplicates=False,
            loaded_files=[],
        )
        import_how.do_thumbnail_above(self.config.get_thumbnails_limit())
        # Generate TSV
        req_values = self.req.values
        if req_values.get(SimpleImportFields.userlb, ""):
            import_how.found_users["user"] = {
                "id": req_values.get(SimpleImportFields.userlb)
            }
            req_values[SimpleImportFields.userlb] = "user"
        if req_values.get(SimpleImportFields.status, ""):
            req_values[SimpleImportFields.status] = classif_qual.get(
                req_values[SimpleImportFields.status], ""
            )
        self.make_tsv(source_bundle, images)
        # Import
        nb_image_files = len(images)
        nb_images = source_bundle.do_import(
            import_where, import_how, nb_image_files, self.report_progress
        )
        self.session.commit()

        # Recompute stats and so on
        ProjectBO.do_after_load(self.session, self.prj_id)
        self.session.commit()

        self.set_job_result(errors=errors, infos={"nb_images": nb_images})

    # Form fields to TSV values
    # TODO: Repeated constants from Mappings.py
    FORM_TO_FIELD = {
        SimpleImportFields.imgdate: "object_date",
        SimpleImportFields.imgtime: "object_time",
        SimpleImportFields.latitude: "object_lat",
        SimpleImportFields.longitude: "object_lon",
        SimpleImportFields.depthmin: "object_depth_min",
        SimpleImportFields.depthmax: "object_depth_max",
        SimpleImportFields.taxolb: "object_annotation_category_id",
        SimpleImportFields.userlb: "object_annotation_person_name",
        SimpleImportFields.status: "object_annotation_status",
    }
    FIELD_TO_FORM: Dict[str, SimpleImportFields] = {
        v: k for k, v in FORM_TO_FIELD.items()
    }
    TSV_FIELDS: List[str] = sorted([k for k in FIELD_TO_FORM.keys()])
    TEXT_FIELDS = (
        "object_date",
        "object_time",
        "object_annotation_status",
        "object_annotation_person_name",
    )

    def make_header(self) -> str:
        """TSV header lines"""
        names = ["object_id", "img_file_name"]
        names.extend(self.TSV_FIELDS)
        types = ["[t]", "[t]"]
        types.extend(
            map(
                lambda fld: "[t]" if fld in self.TEXT_FIELDS else "[n]", self.TSV_FIELDS
            )
        )
        return "\t".join(names) + "\n" + "\t".join(types) + "\n"

    def make_line(self, an_image: str) -> str:
        """
        Generate a TSV line from values
        """
        unq_id = hashlib.md5()
        unq_id.update(bytes(str(an_image), encoding="utf-8"))
        obj_id = unq_id.hexdigest()
        tsv_vals: List[Optional[str]] = [obj_id, an_image]
        req_values = self.req.values
        tsv_vals.extend(
            map(
                lambda fld: req_values.get(self.FIELD_TO_FORM[fld], ""), self.TSV_FIELDS
            )
        )
        tsv_vals_no_none = ["" if v is None else v for v in tsv_vals]
        return "\t".join(tsv_vals_no_none) + "\n"

    def make_tsv(self, bundle: InBundle, images: List[Path]):
        """
        Generate a TSV file from values, inject it into the bundle.
        """
        # TODO: Duplicated code
        dest_file = Path(
            self.temp_for_jobs.in_base_dir_for(self.job_id, "import_meta.tsv")
        )
        with open(dest_file, "w", encoding="utf-8-sig") as fp:
            fp.write(self.make_header())
            for an_image in images:
                tsv_line = self.make_line(str(an_image))
                fp.write(tsv_line)
        bundle.add_tsv(dest_file)

    VALIDATIONS = {
        "imgdate": ObjectHeader.date_from_txt,
        "imgtime": ObjectHeader.time_from_txt,
        "latitude": ObjectHeader.latitude_from_txt,
        "longitude": ObjectHeader.longitude_from_txt,
        "depthmin": ObjectHeader.depth_from_txt,
        "depthmax": ObjectHeader.depth_from_txt,
        "taxolb": lambda x: int(x),
        "userlb": lambda x: int(x),
        "status": lambda x: x,
    }

    def _validate(self) -> SimpleImportRsp:
        """
        Basic validation of values.
        """
        errors = []
        if len(self.req.source_path) == 0:
            errors.append("No file provided.")
        values = self.req.values
        for a_key, a_val in values.items():
            if a_val is None:
                continue
            valid_def = self.VALIDATIONS.get(a_key)
            if not valid_def:
                continue
            try:
                valid_def(a_val)
            except ValueError:
                errors.append("'%s' is not a valid value for %s" % (a_val, a_key))
        ret = SimpleImportRsp(errors=errors, job_id=0)
        return ret
