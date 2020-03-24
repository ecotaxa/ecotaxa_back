# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import csv
import datetime
import logging
import sys
import zipfile
from pathlib import Path

from PIL import Image as PIL_Image
# noinspection PyProtectedMember
from sqlalchemy.engine import ResultProxy

from db.Object import classif_qual_revert
from tasks.ImportBase import ImportBase
from utils import none_to_empty, decode_equal_list, to_float, convert_degree_minute_float_to_decimal_degree, \
    clean_value_and_none


class ImportStep1(ImportBase):

    def __init__(self):
        super().__init__()
        # Received from parameters
        self.intra_step = 0
        self.step_errors = []
        self.input_path: str = ""
        # The row count seen at previous step
        self.total_row_count = 0

    def run(self):
        super().prepare_run()
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logging.info("loaded_files = %s", loaded_files)

        warn_messages = []
        if self.intra_step == 0:
            # Subtask 1, unzip or point to source directory
            self.unzip_if_needed()
            self.intra_step = 1

        if self.intra_step == 1:
            # Validate files
            if self.do_intra_step_1(loaded_files, warn_messages):
                # If anything went wrong we loop on this state
                self.intra_step = 2

        if self.intra_step == 2:
            logging.info("Start Sub Step 1.2")
            # Resolve users
            not_found_user = self.resolve_users()

            # And taxonomy
            not_found_taxo = self.resolve_taxo_found(self.taxo_found)
            if len(not_found_taxo) > 0:
                logging.info("Some Taxo Not Found = %s", not_found_taxo)

            # raise Exception("TEST")
            if len(not_found_user) == 0 and len(not_found_taxo) == 0 and len(warn_messages) == 0:
                # all OK, proceed straight away to step2
                # TODO
                pass
                # self.SPStep2()
            else:
                self.task.taskstate = "Question"
            if len(warn_messages) > 0:
                self.update_progress(1, "Unzip File on temporary folder")
            else:
                self.update_progress(1, "Unzip File on temporary folder")
            # sinon on pose une question

    def do_intra_step_1(self, loaded_files, warn_messages):
        # Reset at each attempt
        self.mapping = {}
        # Import existing mapping into project
        # TODO: Use mapping class
        for k, v in decode_equal_list(self.prj.mappingobj).items():
            self.mapping['object_' + v] = {'table': 'obj_field', 'title': v, 'type': k[0], 'field': k}
        for k, v in decode_equal_list(self.prj.mappingsample).items():
            self.mapping['sample_' + v] = {'table': 'sample', 'title': v, 'type': k[0], 'field': k}
        for k, v in decode_equal_list(self.prj.mappingacq).items():
            self.mapping['acq_' + v] = {'table': 'acq', 'title': v, 'type': k[0], 'field': k}
        for k, v in decode_equal_list(self.prj.mappingprocess).items():
            self.mapping['process_' + v] = {'table': 'process', 'title': v, 'type': k[0], 'field': k}
        project_was_empty = len(self.mapping) == 0
        # Reset at each attempt
        self.taxo_found = {}
        self.found_users = {}
        # Reset errors
        self.step_errors = []
        existing_objects_and_image = self.fetch_existing_images()
        logging.info("SubTask1 : Analyze TSV Files")
        self.update_progress(1, "Unzip File into temporary folder")
        # We have "free" fields at the end of each target DB table, e.g. n00 in ObjectField, or t05 in Sample.
        # Following variable helps tracking their usage.
        last_numbers = {x: {'n': 0, 't': 0} for x in self.PossibleTables}
        for m in self.mapping.values():
            v = int(m['field'][1:])
            if v > last_numbers[m['table']][m['field'][0]]:
                last_numbers[m['table']][m['field'][0]] = v
        source_dir = Path(self.source_dir_or_zip)
        self.total_row_count = 0
        # record fields for which some values are present
        cols_seen = set()
        # taxonomy ids @see Taxonomy
        classif_id_seen = set()
        nb_objects_without_gps = 0
        for a_csv_file in self.possible_tsv_files(source_dir):
            relative_file = a_csv_file.relative_to(source_dir)
            # relative name for logging and recording what was done
            relative_name: str = relative_file.as_posix()
            if relative_name in loaded_files and self.skip_already_loaded_file == 'Y':
                logging.info("File %s skipped, already loaded" % relative_name)
                continue
            logging.info("Analyzing file %s" % relative_name)

            a_csv_file, was_uvpv6 = self.handle_uvpapp_format(a_csv_file, relative_file)

            with open(a_csv_file.as_posix(), encoding='latin_1') as csvfile:
                # Read as a dict, first line gives the format
                rdr = csv.DictReader(csvfile, delimiter='\t', quotechar='"')
                # Read types line (2nd line in file)
                type_line = {field.strip(" \t").lower(): v for field, v in rdr.__next__().items()}
                # Cleanup field names, keeping original ones as key
                clean_fields = {field: field.strip(" \t").lower() for field in rdr.fieldnames}
                # Extract field list from header cooked by CSV reader
                field_list = [clean_fields[field] for field in rdr.fieldnames]
                # Validation of TSV structure
                self.validate_tsv_structure(relative_name, field_list, project_was_empty, last_numbers, type_line,
                                            warn_messages)
                # Validation of TSV content
                nb_no_gps_4_csv, row_count_for_csv = self.validate_tsv_content(relative_name, rdr, clean_fields,
                                                                               a_csv_file, classif_id_seen,
                                                                               cols_seen,
                                                                               existing_objects_and_image)
                nb_objects_without_gps += nb_no_gps_4_csv
                logging.info("File %s : %d row analysed", relative_name, row_count_for_csv)
                self.total_row_count += row_count_for_csv

        if self.total_row_count == 0:
            self.log_for_user(
                "No object to import. It maybe due to :<br>"
                "*  Empty TSV table<br>"
                "*  TSV table already imported => 'SKIP TSV' option should be enabled")
        # print(self.mapping)
        if len(classif_id_seen) > 0:
            self.check_classif(classif_id_seen)
        self.update_progress(1, "Unzip File on temporary folder")
        logging.info("Taxo Found = %s", self.taxo_found)
        logging.info("Users Found = %s", self.found_users)
        not_seen_fields = [k for k in self.mapping if k not in cols_seen]
        logging.info("For Information, not seen fields %s", not_seen_fields)
        if len(not_seen_fields) > 0:
            warn_messages.append("Some fields configured in the project are not seen in this import {0} "
                                 .format(", ".join(not_seen_fields)))
        if nb_objects_without_gps > 0:
            warn_messages.append("{0} objects doesn't have GPS information  ".format(nb_objects_without_gps))
        if len(self.step_errors) > 0:
            self.task.taskstate = "Error"
            self.task.progressmsg = "Some errors founds during file parsing "
            logging.error(self.task.progressmsg)
            self.session.commit()
            return False
        return True

    def validate_tsv_content(self, relative_name, rdr, clean_fields, a_csv_file, classif_id_seen, cols_seen,
                             existing_objects_and_image):
        row_count_for_csv = 0
        nb_objects_without_gps = 0
        vals_cache = {}
        for lig in rdr:
            row_count_for_csv += 1

            latitude_seen = self.validate_tsv_line(relative_name, lig, clean_fields, classif_id_seen, cols_seen,
                                                   vals_cache)

            if not latitude_seen:
                nb_objects_without_gps += 1

            # Verify the image file
            object_id = clean_value_and_none(lig.get('object_id', ''))
            if object_id == '':
                self.log_for_user("Missing object_id in line '%s' of file %s. "
                                  % (row_count_for_csv, relative_name))
            img_file_name = clean_value_and_none(lig.get('img_file_name', 'MissingField img_file_name'))
            img_file_path = a_csv_file.parent / img_file_name
            if not img_file_path.exists():
                self.log_for_user("Missing Image '%s' in file %s. "
                                  % (img_file_name, relative_name))
            else:
                # noinspection PyBroadException
                try:
                    _im = PIL_Image.open(img_file_path.as_posix())
                except:
                    self.log_for_user("Error while reading Image '%s' in file %s. %s"
                                      % (img_file_name, relative_name, sys.exc_info()[0]))

            # Verify duplicate images
            key_exist_obj = "%s*%s" % (object_id, img_file_name)
            if self.skip_object_duplicate != 'Y' and key_exist_obj in existing_objects_and_image:
                self.log_for_user("Duplicate object %s Image '%s' in file %s. "
                                  % (object_id, img_file_name, relative_name))
            existing_objects_and_image.add(key_exist_obj)

        return nb_objects_without_gps, row_count_for_csv

    def validate_tsv_line(self, relative_name, lig, clean_fields, classif_id_seen, cols_seen,
                          vals_cache) -> bool:
        latitude_was_seen = False
        for raw_field, a_field in clean_fields.items():
            m = self.mapping.get(a_field)
            # No mapping, not stored
            if m is None:
                continue
            raw_val = lig.get(raw_field)
            # Try to get the value from the cache
            cache_key = (raw_field, raw_val)
            if cache_key in vals_cache:
                continue
            vals_cache[cache_key] = 1
            # Not seen already, proceed
            csv_val = clean_value_and_none(raw_val)
            cols_seen.add(a_field)
            # From V1.1, if column is present then it's considered as seen.
            #  Before, the criterion was 'at least one value'.
            if csv_val == '':
                # If no relevant value, leave field as NULL
                continue
            if a_field == 'object_lat':
                latitude_was_seen = True
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf < -90 or vf > 90:
                    self.log_for_user("Invalid Lat. value '%s' for Field '%s' in file %s. "
                                      "Incorrect range -90/+90°."
                                      % (csv_val, raw_field, relative_name))
            elif a_field == 'object_lon':
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf < -180 or vf > 180:
                    self.log_for_user("Invalid Long. value '%s' for Field '%s' in file %s. "
                                      "Incorrect range -180/+180°."
                                      % (csv_val, raw_field, relative_name))
            elif m['type'] == 'n':
                vf = to_float(csv_val)
                if vf is None:
                    self.log_for_user("Invalid float value '%s' for Field '%s' in file %s."
                                      % (csv_val, raw_field, relative_name))
                elif a_field == 'object_annotation_category_id':
                    classif_id_seen.add(int(csv_val))
            elif a_field == 'object_date':
                try:
                    datetime.date(int(csv_val[0:4]), int(csv_val[4:6]), int(csv_val[6:8]))
                except ValueError:
                    self.log_for_user("Invalid Date value '%s' for Field '%s' in file %s."
                                      % (csv_val, raw_field, relative_name))
            elif a_field == 'object_time':
                try:
                    csv_val = csv_val.zfill(6)
                    datetime.time(int(csv_val[0:2]), int(csv_val[2:4]), int(csv_val[4:6]))
                except ValueError:
                    self.log_for_user("Invalid Time value '%s' for Field '%s' in file %s."
                                      % (csv_val, raw_field, relative_name))
            elif a_field == 'object_annotation_category':
                if clean_value_and_none(lig.get('object_annotation_category_id', '')) == '':
                    # Apply the mapping
                    csv_val = self.taxo_mapping.get(csv_val.lower(), csv_val)
                    # Record that the taxo was seen
                    self.taxo_found[csv_val.lower()] = None
            elif a_field == 'object_annotation_person_name':
                maybe_email = clean_value_and_none(lig.get('object_annotation_person_email', ''))
                self.found_users[csv_val.lower()] = {'email': maybe_email}
            elif a_field == 'object_annotation_status':
                if csv_val != 'noid' and csv_val.lower() not in classif_qual_revert:
                    self.log_for_user("Invalid Annotation Status '%s' for Field '%s' in file %s."
                                      % (csv_val, raw_field, relative_name))
        return latitude_was_seen

    def validate_tsv_structure(self, relative_name, field_list, project_was_empty, last_numbers, type_line,
                               warn_messages):
        a_field: str
        for a_field in field_list:
            if a_field in self.mapping:
                # Field already mapped
                continue
            splitted_col = a_field.split("_", 1)
            if len(splitted_col) != 2:
                self.log_for_user(
                    "Invalid Header '%s' in file %s. Format must be Table_Field. Field ignored" % (
                        a_field, relative_name))
                continue
            target_table = splitted_col[0]
            if a_field in self.PredefinedFields:
                _target_table = self.PredefinedFields[a_field]['table']
                self.mapping[a_field] = self.PredefinedFields[a_field]
            elif a_field in self.ProgFields:
                # Not mapped, but not a free field
                pass
            else:  # not a predefined field, so nXX ou tXX
                if target_table == "object":
                    target_table = "obj_field"
                if target_table not in self.PossibleTables:
                    self.log_for_user(
                        "Invalid Header '%s' in file %s. Table Incorrect. Field ignored" % (
                            a_field, relative_name))
                    continue
                if target_table not in ('obj_head', 'obj_field'):
                    # In other tables, all types are forced to text
                    sel_type = 't'
                else:
                    sel_type = self.PossibleTypes.get(type_line[a_field])
                    if sel_type is None:
                        self.log_for_user("Invalid Type '%s' for Field '%s' in file %s. "
                                          "Incorrect Type. Field ignored" % (type_line[a_field],
                                                                             a_field,
                                                                             relative_name))
                        continue
                last_numbers[target_table][sel_type] += 1
                self.mapping[a_field] = {'table': target_table,
                                         'field': sel_type + "%02d" % last_numbers[target_table][sel_type],
                                         'type': sel_type, 'title': splitted_col[1]}
                logging.info("New field %s found in file %s", a_field, relative_name)
                if not project_was_empty:
                    warn_messages.append(
                        "New field %s found in file %s" % (a_field, relative_name))

    def resolve_users(self):
        # Resolve TSV names from DB names or emails
        names = [x for x in self.found_users.keys()]
        emails = [x.get('email') for x in self.found_users.values()]
        res: ResultProxy = self.session.execute(
            "SELECT id, lower(name), lower(email) "
            "  FROM users "
            " WHERE lower(name) = ANY(:nms) or email = ANY(:ems) ",
            {"nms": names, "ems": emails})
        for rec in res:
            for u in self.found_users:
                if u == rec[1] or none_to_empty(self.found_users[u].get('email')).lower() == rec[2]:
                    self.found_users[u]['id'] = rec[0]
        logging.info("Users Found = %s", self.found_users)
        not_found_user = [k for k, v in self.found_users.items() if v.get("id") is None]
        if len(not_found_user) > 0:
            logging.info("Some Users Not Found = %s", not_found_user)
        return not_found_user

    def check_classif(self, classif_id_seen):
        res: ResultProxy = self.session.execute("SELECT id "
                                                "  FROM taxonomy "
                                                " WHERE id = ANY (:een)",
                                                {"een": list(classif_id_seen)})
        classif_id_found_in_db = {int(r['id']) for r in res}
        classif_id_not_found_in_db = classif_id_seen.difference(classif_id_found_in_db)
        if len(classif_id_not_found_in_db) > 0:
            msg = "Some specified classif_id don't exist, correct them prior to reload: %s" % (
                ",".join([str(x) for x in classif_id_not_found_in_db]))
            self.step_errors.append(msg)
            logging.error(msg)

    def unzip_if_needed(self):
        if self.input_path.lower().endswith("zip"):
            logging.info("SubTask0 : Unzip File into temporary folder")
            self.update_progress(1, "Unzip File into temporary folder")
            self.source_dir_or_zip = self.temptask.data_dir_for(self.task_id)
            with zipfile.ZipFile(self.input_path, 'r') as z:
                z.extractall(self.source_dir_or_zip)
        else:
            self.source_dir_or_zip = self.input_path
