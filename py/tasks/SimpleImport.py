# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import hashlib
from pathlib import Path
from typing import List

from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping
from BO.helpers.ImportHelpers import ImportWhere, ImportHow
from api.imports import SimpleImportReq, SimpleImportRsp
from db.Object import Object, classif_qual
from tasks.DBWriter import DBWriter
from tasks.Import import ImportServiceBase
from tech.DynamicLogs import get_logger

logger = get_logger(__name__)


class SimpleImport(ImportServiceBase):
    """
        Simple import, i.e. many images with same metadata.
    """
    req: SimpleImportReq  # Not used, just for typings

    def __init__(self, prj_id: int, req: SimpleImportReq):
        super().__init__(prj_id, req)

    def run(self) -> SimpleImportRsp:
        # Validate values in all cases
        ret = self._validate()
        if len(ret.errors) > 0:
            return ret
        if self.task_id != 0:
            if len(ret.errors) == 0:
                ret = self.do_import()
        return ret

    def do_import(self):
        """
            Do the real job, i.e. copy files while creating records.
        """
        self.prepare_run()
        errors = []
        self.manage_uploaded()
        self.unzip_if_needed()
        # Use a Bundle
        source_bundle = InBundle(self.source_dir_or_zip, Path(self.temp_for_task.data_dir_for(self.task_id)))
        # Clean it, in case the ZIP contains a CSV
        source_bundle.remove_all_tsvs()
        images = source_bundle.list_image_files()
        # Configure the import to come, destination
        db_writer = DBWriter(self.session)
        import_where = ImportWhere(db_writer, self.vault, self.temp_for_task.base_dir_for(self.task_id))
        # Configure the import to come, directives
        import_how = ImportHow(prj_id=self.prj_id, update_mode="", custom_mapping=ProjectMapping(),
                               skip_object_duplicates=False, loaded_files=[])
        import_how.do_thumbnail_above(int(self.config['THUMBSIZELIMIT']))
        # Generate TSV
        req_values = self.req.values
        if req_values.get("userlb", ""):
            import_how.found_users["user"] = {"id": req_values.get("userlb")}
            req_values["userlb"] = "user"
        if req_values.get("status", ""):
            req_values["status"] = classif_qual.get(req_values["status"], "")
        self.make_tsv(source_bundle, images)
        # Import
        nb_image_files = len(images)
        nb_images = source_bundle.do_import(import_where, import_how, nb_image_files, self.report_progress)

        self.do_after_load()
        ret = SimpleImportRsp(errors=errors,
                              nb_images=nb_images)
        return ret

    # Form fields to TSV values
    FORM_TO_FIELD = {"imgdate": 'object_date',
                     "imgtime": 'object_time',
                     "latitude": 'object_lat',
                     "longitude": 'object_lon',
                     "depthmin": 'object_depth_min',
                     "depthmax": 'object_depth_max',
                     "taxolb": 'object_annotation_category_id',
                     "userlb": 'object_annotation_person_name',
                     "status": 'object_annotation_status'}
    FIELD_TO_FORM = {v: k for k, v in FORM_TO_FIELD.items()}
    TSV_FIELDS = sorted([k for k in FIELD_TO_FORM.keys()])
    TEXT_FIELDS = ('object_date', 'object_time', 'object_annotation_status', 'object_annotation_person_name')

    def make_header(self) -> str:
        """ TSV header lines """
        names = ['object_id', 'img_file_name']
        names.extend(self.TSV_FIELDS)
        types = ['[t]', '[t]']
        types.extend(map(lambda fld: '[t]' if fld in self.TEXT_FIELDS else '[n]', self.TSV_FIELDS))
        return "\t".join(names) + "\n" + "\t".join(types) + "\n"

    def make_line(self, an_image: str) -> str:
        """ Generate a TSV line from values """
        unq_id = hashlib.md5()
        unq_id.update(bytes(str(an_image), encoding="utf-8"))
        obj_id = unq_id.hexdigest()
        tsv_vals = [obj_id, an_image]
        tsv_vals.extend(map(lambda fld: self.req.values.get(self.FIELD_TO_FORM[fld], ""), self.TSV_FIELDS))
        return '\t'.join(tsv_vals) + "\n"

    def make_tsv(self, bundle: InBundle, images: List[Path]):
        """
            Generate a TSV from values, inject it into the bundle.
        """
        dest_file = Path(self.temp_for_task.in_base_dir_for(self.task_id, "import_meta.tsv"))
        with open(dest_file, "w", encoding='latin_1') as fp:
            fp.write(self.make_header())
            for an_image in images:
                tsv_line = self.make_line(str(an_image))
                fp.write(tsv_line)
        bundle.add_tsv(dest_file)

    VALIDATIONS = {"imgdate": Object.date_from_txt,
                   "imgtime": Object.time_from_txt,
                   "latitude": Object.latitude_from_txt,
                   "longitude": Object.longitude_from_txt,
                   "depthmin": Object.depth_from_txt,
                   "depthmax": Object.depth_from_txt,
                   "taxolb": lambda x: int(x),
                   "userlb": lambda x: int(x),
                   "status": lambda x: x}

    def _validate(self) -> SimpleImportRsp:
        """
            Basic validation of values.
        """
        errors = []
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
        ret = SimpleImportRsp(errors=errors,
                              nb_images=0)
        return ret