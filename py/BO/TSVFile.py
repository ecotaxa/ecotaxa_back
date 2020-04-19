# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import csv
import datetime
import logging
import random
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Set, Optional

# noinspection PyPackageRequirements
from PIL import Image as PIL_Image
# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from BO.Mappings import GlobalMapping, ProjectMapping
from BO.SpaceTime import compute_sun_position, astral_cache
from BO.helpers.ImportHelpers import ImportHow, ImportWhere, ImportDiagnostic
from db.Image import Image
from db.Object import classif_qual_revert
from utils import clean_value, none_to_empty, to_float, convert_degree_minute_float_to_decimal_degree, \
    clean_value_and_none

logger = logging.getLogger(__name__)


class TSVFile(object):
    """
        A tab-separated file, index of images with additional information about them.
    """

    # Fields which are not mapped, i.e. not directly destined to DB, but needed here for fallback values.
    ProgFields = {'object_annotation_time',
                  'object_annotation_person_email',
                  # 'annotation_person_first_name' # historical
                  }

    def __init__(self, full_path: Path, parent_path: Path):
        self.path = full_path
        relative_file = full_path.relative_to(parent_path)
        # relative name for logging and recording what was done
        self.relative_name: str = relative_file.as_posix()

        # when open()-ed, below members are active
        self.rdr: Optional[csv.DictReader] = None
        # key: not normalized field, from TSV header e.g. "\t ObJect_laT "
        # value: normalized field i.e. "object_lat"
        self.clean_fields: Optional[OrderedDict[str, str]] = None
        # The 2nd line, with types
        # key: normalized field
        # value: TSV type e.g. [f]
        self.type_line: Optional[Dict[str, str]] = None

    def open(self):
        csv_file = open(self.path.as_posix(), encoding='latin_1')
        # Read as a dict, first line gives the format
        self.rdr = csv.DictReader(csv_file, delimiter='\t', quotechar='"')
        # Cleanup field names, keeping original ones as key.
        clean_fields = OrderedDict()
        for raw_field in self.rdr.fieldnames:
            clean_fields[raw_field] = raw_field.strip(" \t").lower()
        self.clean_fields = clean_fields
        # Read types line (2nd line in file)
        line_2 = self.rdr.__next__()
        self.type_line = {clean_fields[raw_field]: v for raw_field, v in line_2.items()}
        # When called using "with", the file will be closed on code block leave
        return csv_file

    REPORT_EVERY = 100

    def do_import(self, where: ImportWhere, how: ImportHow, counter: int, call_every_chunk) -> int:
        """
            Import self into DB.
        """
        session = where.db_writer.session
        with self.open():
            # Only keep the fields we can persist, the ones ignored at first step would be signalled here as well
            # if we didn't prohibit the move to 2nd step in this case.
            field_set = set(self.clean_fields.values())
            field_set = self.filter_unused_fields(how.custom_mapping, field_set) - self.ProgFields

            # We can now prepare ORM classes with optimal performance
            target_fields = self.dispatch_fields_by_table(how.custom_mapping, field_set)
            ObjectGen, ObjectFieldsGen, ImageGen = where.db_writer.generators(target_fields)

            # For annotation, if there is both an id and a category then ignore category
            ignore_annotation_category: bool = 'object_annotation_category_id' in field_set \
                                               and 'object_annotation_category' in field_set

            vals_cache = dict()
            # Loop over all lines
            row_count_for_csv = 0
            for rawlig in self.rdr:
                # Bean counting
                row_count_for_csv += 1
                counter += 1

                lig = {self.clean_fields[field]: v for field, v in rawlig.items()}

                # First read into dicts, faster than doing settattr()
                dicts_to_write = {alias: dict() for alias in GlobalMapping.TARGET_CLASSES.keys()}

                if ignore_annotation_category:
                    # Remove category as required, but only if there is really an id value
                    # it can happen that the id is empty, even if table header is present
                    if clean_value(lig.get('object_annotation_category_id', '')) != '':
                        del lig['object_annotation_category']

                # Read TSV line into dicts
                self.read_fields_to_dicts(how, field_set, lig, dicts_to_write, vals_cache)

                # Create SQLAlchemy mappers of the object itself and slaves (1<->1)
                object_head_to_write = ObjectGen(**dicts_to_write["obj_head"])
                object_fields_to_write = ObjectFieldsGen(**dicts_to_write["obj_field"])
                image_to_write = ImageGen(**dicts_to_write["images"])
                # Parents are created the same way, _when needed_ (i.e. nearly never),
                #  in @see add_parent_objects

                try:
                    object_head_to_write.sunpos = compute_sun_position(object_head_to_write)
                except Exception as e:  # pragma: no cover
                    # See astral.py for cases
                    # TODO: Find a test case, e.g. by launching algo onto the whole DB
                    logger.error("Astral error : %s for %s", e, astral_cache)

                self.add_parent_objects(how.prj_id, session, how.existing_parent_ids,
                                        object_head_to_write, dicts_to_write)

                key_exist_obj = "%s*%s" % (object_fields_to_write.orig_id, image_to_write.orig_file_name)
                if key_exist_obj in how.objects_and_images_to_skip:
                    logger.info("Image skipped: %s %s", object_fields_to_write.orig_id, image_to_write.orig_file_name)
                    continue

                must_write_obj = self.create_or_link_slaves(how.prj_id, how.existing_objects, object_fields_to_write,
                                                            object_head_to_write)

                where.db_writer.add_db_entities(object_head_to_write, object_fields_to_write, image_to_write,
                                                must_write_obj)

                how.existing_objects[object_fields_to_write.orig_id] = object_head_to_write.objid

                instead_image = None
                if how.vignette_maker:
                    # If there is need for a vignette, the file named in the TSV is NOT the one written,
                    # and pointed at, by the usual DB line. Instead, it's the vignette.
                    instead_image = how.vignette_maker.make_vignette(image_to_write.orig_file_name)
                    if how.vignette_maker.must_keep_original():
                        # In this case, the original image is kept in another DB line
                        backup_img_to_write = ImageGen(**dicts_to_write["images"])
                        backup_img_to_write.imgrank = 100
                        backup_img_to_write.thumb_file_name = None
                        backup_img_to_write.thumb_width = None
                        backup_img_to_write.thumb_height = None
                        # Store backup image into DB
                        where.db_writer.add_vignette_backup(object_head_to_write, backup_img_to_write)
                        # Store original image
                        orig_file_name = self.path.parent.joinpath(image_to_write.orig_file_name)
                        sub_path = where.vault.store_image(orig_file_name, backup_img_to_write.imgid)
                        backup_img_to_write.file_name = sub_path
                        # Get original image dimensions
                        im = PIL_Image.open(where.vault.path_to(sub_path))
                        backup_img_to_write.width, backup_img_to_write.height = im.size
                        del im

                self.deal_with_images(where, how, image_to_write, instead_image)

                if (counter % self.REPORT_EVERY) == 0:
                    where.db_writer.persist()
                    call_every_chunk(counter)

        return row_count_for_csv

    def filter_unused_fields(self, custom_mapping, field_set: set) -> set:
        """
            Sanitize field list by removing the ones which are not known in mapping, nor used programmatically.
            :param custom_mapping:
            :param field_set:
            :return:
        """
        ok_fields = set([field for field in field_set
                         if field in custom_mapping.all_fields
                         or field in GlobalMapping.PREDEFINED_FIELDS
                         or field in self.ProgFields])
        ko_fields = [field for field in field_set if field not in ok_fields]
        if len(ko_fields) > 0:  # pragma: no cover
            # This cannot happen as step1 prevents it. However the code is left in case API evolves.
            logger.warning("In %s, field(s) %s not used, values will be ignored",
                           self.relative_name, ko_fields)
        return ok_fields

    @staticmethod
    def add_parent_objects(prj_id, session: Session, existing_ids, object_head_to_write, dicts_to_write):
        """
            Assignment of Sample, Acquisition & Process ID, creating them if necessary
            Due to amount of duplicated information in TSV, this happens for few % of rows
             so no real need to optimize here.
        """
        for alias, parent_class in GlobalMapping.PARENT_CLASSES.items():
            dict_to_write = dicts_to_write[alias]
            ids_for_obj = existing_ids[alias]
            # Here we take advantage from consistent naming conventions
            # The 3 involved tables have "orig_id" column serving the same purpose
            parent_orig_id = dict_to_write.get("orig_id")
            if parent_orig_id is None:
                # No way to identify, ignore
                continue
            fk_to_obj = parent_class.pk()
            if parent_orig_id in ids_for_obj:
                # This parent object was known before, don't add it into the session (DB)
                # but link the child object_head to it (like newly created ones below)
                pass
            else:
                # Create the SQLAlchemy wrapper
                obj_to_write = parent_class(**dict_to_write)
                # Link with project
                obj_to_write.projid = prj_id
                session.add(obj_to_write)
                session.flush()
                # We now have a (generated) PK to copy back into objects
                # TODO: Skip the getattr() below in favor of obj_to_write.pk_val()
                ids_for_obj[parent_orig_id] = getattr(obj_to_write, fk_to_obj)
                logger.info("++ IDS %s %s", alias, ids_for_obj)
            # Anyway
            setattr(object_head_to_write, fk_to_obj, ids_for_obj[parent_orig_id])

    @staticmethod
    def dispatch_fields_by_table(custom_mapping: ProjectMapping, field_set: Set) -> Dict[str, Set]:
        """
            Build a set of target DB columns by target table.
        :param custom_mapping:
        :param field_set:
        :return:
        """
        ret = {alias: set() for alias in GlobalMapping.TARGET_CLASSES.keys()}
        for a_field in field_set:
            mapping = GlobalMapping.PREDEFINED_FIELDS.get(a_field)
            if not mapping:
                mapping = custom_mapping.search_field(a_field)
            target_tbl = mapping["table"]
            target_fld = mapping["field"]
            ret[target_tbl].add(target_fld)
        return ret

    @staticmethod
    def read_fields_to_dicts(how: ImportHow, field_set: Set, lig: Dict[str, str], dicts_to_write, vals_cache: Dict):
        """
            Read the data line into target dicts. Values go into the right bucket, i.e. target dict, depending
            on mappings (standard one and per-project custom one).
        """
        predefined_mapping = GlobalMapping.PREDEFINED_FIELDS
        custom_mapping = how.custom_mapping
        # CSV reader returns a minimal dict with no value equal to None
        # so we have values only for common fields.
        for a_field in field_set.intersection(lig.keys()):
            # We have a value
            raw_val = lig.get(a_field)
            # Try to get the transformed value from the cache
            cache_key = (a_field, raw_val)
            cached_field_value = vals_cache.get(cache_key)
            m = predefined_mapping.get(a_field)
            if not m:
                m = custom_mapping.search_field(a_field)
            field_table = m["table"]
            field_name = m["field"]
            if cached_field_value is None:
                csv_val = clean_value(raw_val)
                # If no relevant value, leave field as NULL
                if csv_val == '':
                    continue
                if a_field == 'object_lat':
                    # It's [n] type but since AVPApp they can contain a notation like ddd°MM.SS
                    # which can be [t] as well.
                    cached_field_value = convert_degree_minute_float_to_decimal_degree(csv_val)
                elif a_field == 'object_lon':
                    cached_field_value = convert_degree_minute_float_to_decimal_degree(csv_val)
                elif m['type'] == 'n':
                    cached_field_value = to_float(csv_val)
                elif a_field == 'object_date':
                    cached_field_value = datetime.date(int(csv_val[0:4]), int(csv_val[4:6]), int(csv_val[6:8]))
                elif a_field == 'object_time':
                    csv_val = csv_val.zfill(6)
                    cached_field_value = datetime.time(int(csv_val[0:2]), int(csv_val[2:4]), int(csv_val[4:6]))
                elif field_name == 'classif_when':
                    v2 = clean_value(lig.get('object_annotation_time', '000000')).zfill(6)
                    cached_field_value = datetime.datetime(int(csv_val[0:4]), int(csv_val[4:6]),
                                                           int(csv_val[6:8]), int(v2[0:2]),
                                                           int(v2[2:4]), int(v2[4:6]))
                    # no caching of this one as it depends on another value on same line
                    cache_key = "0"
                elif field_name == 'classif_id':
                    # We map 2 fields to classif_id, the second (text one) has [t] type, treated here.
                    # The first, numeric, version is in "if type=n" case above.
                    csv_val = how.taxo_mapping.get(csv_val.lower(), csv_val)
                    # Use initial mapping
                    cached_field_value = how.taxo_found[none_to_empty(csv_val).lower()]
                elif field_name == 'classif_who':
                    # Eventually map to another user if asked so
                    cached_field_value = how.found_users[none_to_empty(csv_val).lower()].get('id', None)
                elif field_name == 'classif_qual':
                    cached_field_value = classif_qual_revert.get(csv_val.lower())
                else:
                    # Assume it's an ordinary text field with nothing special
                    cached_field_value = csv_val
                # Cache if relevant, setting the cache_key to "0" above effectively voids
                vals_cache[cache_key] = cached_field_value

            # Write the field into the right object
            dict_to_write = dicts_to_write[field_table]
            dict_to_write[field_name] = cached_field_value

    @staticmethod
    def create_or_link_slaves(prj_id, existing_objects: Dict, object_fields_to_write,
                              object_head_to_write) -> bool:
        # It can be a line with a complementary image
        if object_fields_to_write.orig_id in existing_objects:
            logger.info("Second image for %s ", object_fields_to_write.orig_id)
            # Set the objid which will be copied for storing the image
            object_head_to_write.objid = existing_objects[object_fields_to_write.orig_id]
            # In this case just point to previous
            return False
        else:
            # or create it
            object_head_to_write.projid = prj_id
            object_head_to_write.random_value = random.randint(1, 99999999)
            # Below left NULL @see self.update_counts_and_img0
            # object_head_to_write.img0id = XXXXX
            return True

    def deal_with_images(self, where: ImportWhere, how: ImportHow, image_to_write: Image, instead_image: Path = None):
        """
            Generate image, eventually the vignette, create DB line(s) and copy image file into vault.
        :param where:
        :param how:
        :param image_to_write:
        :param instead_image: Store this image instead of the one in Image record.
        :return:
        """
        if instead_image:
            # Source file is a replacement
            img_file_path = instead_image
        else:
            # Files are in a subdirectory for UVPV6, same directory for non-UVPV6
            # TODO: Unsure if it works on Windows, as there is a "/" for UVPV6
            img_file_path = self.path.parent.joinpath(image_to_write.orig_file_name)

        sub_path = where.vault.store_image(img_file_path, image_to_write.imgid)
        image_to_write.file_name = sub_path
        if "imgrank" not in image_to_write:
            image_to_write.imgrank = 0  # default value

        self.dimensions_and_resize(how, where, sub_path, image_to_write)

    @staticmethod
    def dimensions_and_resize(how, where, sub_path, image_to_write):
        im = PIL_Image.open(where.vault.path_to(sub_path))
        image_to_write.width = im.size[0]
        image_to_write.height = im.size[1]
        # Generate a thumbnail if image is too large
        if (im.size[0] > how.max_dim) or (im.size[1] > how.max_dim):
            im.thumbnail((how.max_dim, how.max_dim))
            if im.mode == 'P':
                # (8-bit pixels, mapped to any other mode using a color palette)
                # from https://pillow.readthedocs.io/en/latest/handbook/concepts.html#modes
                # Tested using a PNG with palette
                im = im.convert("RGB")
            thumb_relative_path, thumb_full_path = where.vault.thumbnail_paths(image_to_write.imgid)
            im.save(thumb_full_path)
            image_to_write.thumb_file_name = thumb_relative_path
            image_to_write.thumb_width = im.size[0]
            image_to_write.thumb_height = im.size[1]
        else:
            # Close the PIL image, when resized it was done during im.save
            # Otherwise there is a FD exhaustion on PyPy
            im.close()
            # Need empty fields for bulk insert
            image_to_write.thumb_file_name = None
            image_to_write.thumb_width = None
            image_to_write.thumb_height = None

    def do_validate(self, how: ImportHow, diag: ImportDiagnostic):
        with self.open():
            self.validate_structure(how, diag)
            rows_for_csv = self.validate_content(how, diag)
            return rows_for_csv

    def validate_structure(self, how: ImportHow, diag: ImportDiagnostic):
        """
            TSV ordinary 'structure' is in first text line.
            Our implementation adds a line of expected types in second line.
        """
        a_field: str
        for a_field in self.clean_fields.values():
            # split at first _ as the column name might contain an _
            split_col = a_field.split("_", 1)
            if len(split_col) != 2:
                diag.error("Invalid Header '%s' in file %s. Format must be Table_Field. Field ignored"
                           % (a_field, self.relative_name))
                continue
            if a_field in GlobalMapping.PREDEFINED_FIELDS:
                # OK it's a predefined one
                continue
            if a_field in TSVFile.ProgFields:
                # Not mapped, but not a programmatically-used field
                continue
            # Not a predefined field, so nXX or tXX
            if how.custom_mapping.search_field(a_field):
                # Custom field was already mapped, in a previous import or another TSV of present import
                continue
            # e.g. acq_sn -> acq
            tsv_table_prfx = split_col[0]
            # e.g. acq -> acquisitions
            target_table = GlobalMapping.TSV_table_to_table(tsv_table_prfx)
            if target_table not in GlobalMapping.POSSIBLE_TABLES:
                diag.error("Invalid Header '%s' in file %s. Unknown table prefix. Field ignored"
                           % (a_field, self.relative_name))
                continue
            if target_table not in ('obj_head', 'obj_field'):
                # In other tables, all types are forced to text
                sel_type = 't'
                # TODO: Tell the user that an eventual type is just ignored
            else:
                sel_type = self.type_line[a_field]
                try:
                    sel_type = GlobalMapping.POSSIBLE_TYPES[sel_type]
                except KeyError:
                    diag.error("Invalid Type '%s' for Field '%s' in file %s. "
                               "Incorrect Type. Field ignored"
                               % (sel_type, a_field, self.relative_name))
                    continue
            # Add the new custom column
            target_col = split_col[1]
            how.custom_mapping.add_column(target_table, tsv_table_prfx, target_col, sel_type)
            logger.info("New field %s found in file %s", a_field, self.relative_name)
            # Warn that project settings were extended, i.e. empty columns
            if not how.custom_mapping.was_empty:
                diag.warn("New field %s found in file %s" % (a_field, self.relative_name))

    def validate_content(self, how: ImportHow, diag: ImportDiagnostic):
        row_count_for_csv = 0
        vals_cache = {}
        for lig in self.rdr:
            row_count_for_csv += 1

            self.validate_line(how, diag, lig, vals_cache)

            # Verify the image file
            object_id = clean_value_and_none(lig.get('object_id', ''))
            if object_id == '':
                diag.error("Missing object_id in line '%s' of file %s. "
                           % (row_count_for_csv, self.relative_name))
            img_file_name = clean_value_and_none(lig.get('img_file_name', 'MissingField img_file_name'))
            # Below works as well for UVPV6, as the file 'name' is in fact a relative path,
            # e.g. 'sub1/20200205-111823_3.png'
            img_file_path = self.path.parent / img_file_name
            if not img_file_path.exists():
                diag.error("Missing Image '%s' in file %s. "
                           % (img_file_name, self.relative_name))
            else:
                # noinspection PyBroadException
                try:
                    _im = PIL_Image.open(img_file_path.as_posix())
                except Exception as _e:
                    diag.error("Error while reading Image '%s' in file %s. %s"
                               % (img_file_name, self.relative_name, sys.exc_info()[0]))

            # Verify duplicate images
            key_exist_obj = "%s*%s" % (object_id, img_file_name)
            if not how.skip_object_duplicates:
                # Ban the duplicates, except if we can skip them.
                if key_exist_obj in diag.existing_objects_and_image:
                    diag.error("Duplicate object '%s' Image '%s' in file %s. "
                               % (object_id, img_file_name, self.relative_name))
            diag.existing_objects_and_image.add(key_exist_obj)

        return row_count_for_csv

    def validate_line(self, how: ImportHow, diag: ImportDiagnostic, lig, vals_cache):
        """
            Validate a line from data point of view.
        :param how:
        :param diag:
        :param lig:
        :param vals_cache:
        :return:
        """
        latitude_was_seen = False
        predefined_mapping = GlobalMapping.PREDEFINED_FIELDS
        custom_mapping = how.custom_mapping
        for raw_field, a_field in self.clean_fields.items():
            m = predefined_mapping.get(a_field)
            if m is None:
                m = custom_mapping.search_field(a_field)
                # No mapping, not stored
                if m is None:
                    continue
            raw_val = lig.get(raw_field)
            # Try to get the value from the cache
            cache_key = (raw_field, raw_val)
            if cache_key in vals_cache:
                if a_field == 'object_lat':
                    latitude_was_seen = True
                continue
            vals_cache[cache_key] = 1
            # Same column with same value was not seen already, proceed
            csv_val = clean_value_and_none(raw_val)
            diag.cols_seen.add(a_field)
            # From V1.1, if column is present then it's considered as seen.
            #  Before, the criterion was 'at least one value'.
            if csv_val == '':
                # If no relevant value, leave field as NULL
                continue
            if a_field == 'object_lat':
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf < -90 or vf > 90:
                    diag.error("Invalid Lat. value '%s' for Field '%s' in file %s. "
                               "Incorrect range -90/+90°."
                               % (csv_val, raw_field, self.relative_name))
                    del vals_cache[cache_key]
                else:
                    latitude_was_seen = True
            elif a_field == 'object_lon':
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf < -180 or vf > 180:
                    diag.error("Invalid Long. value '%s' for Field '%s' in file %s. "
                               "Incorrect range -180/+180°."
                               % (csv_val, raw_field, self.relative_name))
            elif m['type'] == 'n':
                vf = to_float(csv_val)
                if vf is None:
                    diag.error("Invalid float value '%s' for Field '%s' in file %s."
                               % (csv_val, raw_field, self.relative_name))
                elif a_field == 'object_annotation_category_id':
                    diag.classif_id_seen.add(int(csv_val))
            elif a_field == 'object_date':
                try:
                    datetime.date(int(csv_val[0:4]), int(csv_val[4:6]), int(csv_val[6:8]))
                except ValueError:
                    diag.error("Invalid Date value '%s' for Field '%s' in file %s."
                               % (csv_val, raw_field, self.relative_name))
            elif a_field == 'object_time':
                try:
                    csv_val = csv_val.zfill(6)
                    datetime.time(int(csv_val[0:2]), int(csv_val[2:4]), int(csv_val[4:6]))
                except ValueError:
                    diag.error("Invalid Time value '%s' for Field '%s' in file %s."
                               % (csv_val, raw_field, self.relative_name))
            elif a_field == 'object_annotation_category':
                if clean_value_and_none(lig.get('object_annotation_category_id', '')) == '':
                    # Apply the mapping, if and only if there is no id
                    csv_val = how.taxo_mapping.get(csv_val.lower(), csv_val)
                    # Record that the taxon was seen
                    how.taxo_found[csv_val.lower()] = None
            elif a_field == 'object_annotation_person_name':
                maybe_email = clean_value_and_none(lig.get('object_annotation_person_email', ''))
                # TODO: It's more "diag" than "how"
                how.found_users[csv_val.lower()] = {'email': maybe_email}
            elif a_field == 'object_annotation_status':
                if csv_val != 'noid' and csv_val.lower() not in classif_qual_revert:
                    diag.error("Invalid Annotation Status '%s' for Field '%s' in file %s."
                               % (csv_val, raw_field, self.relative_name))
        # Update missing GPS count
        if not latitude_was_seen:
            diag.nb_objects_without_gps += 1
