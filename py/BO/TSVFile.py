# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import csv
import datetime
import logging
import random
import shutil
import sys
from pathlib import Path, PurePath
from typing import Dict

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

    def do_import(self, where: ImportWhere, how: ImportHow,
                  counter: int, call_every_chunk) -> int:
        """
            Import self into DB.
        """
        session = where.db_writer.session
        with open(self.path.as_posix(), encoding='latin_1') as csv_file:
            # Read as a dict, first line gives the format
            rdr = csv.DictReader(csv_file, delimiter='\t', quotechar='"')
            # Read types line (2nd line in file). This line is ignored.
            _type_line = {field: v for field, v in rdr.__next__().items()}
            # Cleanup field names, keeping original ones as key
            clean_fields = {field: field.strip(" \t").lower() for field in rdr.fieldnames}
            # Extract field list from header cooked by CSV reader
            field_set = set([clean_fields[field] for field in rdr.fieldnames])
            # Only keep the fields we can persist
            field_set = self.filter_unused_fields(how.custom_mapping, field_set)

            # Remove fields which are unknown in ORM
            target_fields = {alias: set() for alias in GlobalMapping.target_classes.keys()}
            field_set = self.filter_not_in_db_fields(how.custom_mapping, field_set, target_fields)

            # We can now prepare ORM classes with optimal performance
            ObjectGen, ObjectFieldsGen, ImageGen = where.db_writer.generators(target_fields)

            # For annotation, if there is both an id and a category then ignore category
            ignore_annotation_category: bool = 'object_annotation_category_id' in field_set \
                                               and 'object_annotation_category' in field_set

            vals_cache = dict()
            # Loop over all lines
            row_count_for_csv = 0
            for rawlig in rdr:
                # Bean counting
                row_count_for_csv += 1
                counter += 1

                lig = {clean_fields[field]: v for field, v in rawlig.items()}

                # First read into dicts, faster than doing settattr()
                dicts_to_write = {alias: dict() for alias in GlobalMapping.target_classes.keys()}

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
                except Exception as e:
                    # e.g. in case of invalid time
                    logger.error("Astral error : %s for %s", e, astral_cache)

                self.add_parent_objects(how.prj_id, session, how.existing_parent_ids, object_head_to_write,
                                        dicts_to_write)

                key_exist_obj = "%s*%s" % (object_fields_to_write.orig_id, image_to_write.orig_file_name)
                if key_exist_obj in how.objects_and_images_to_skip:
                    continue

                must_write_obj = self.create_or_link_slaves(how.prj_id, how.existing_objects, object_fields_to_write,
                                                            object_head_to_write)

                where.db_writer.add_db_entities(object_head_to_write, object_fields_to_write, image_to_write,
                                                must_write_obj)

                how.existing_objects.add(object_fields_to_write.orig_id)

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
                        where.db_writer.add_vignette_backup(object_head_to_write, backup_img_to_write)
                        # Store original image
                        orig_file_name = self.path.parent.joinpath(image_to_write.orig_file_name)
                        dest_img_path, _dummy1, _dummy1, _dummy1 = self.store_into_vault(where.vault,
                                                                                         orig_file_name,
                                                                                         backup_img_to_write)
                        # Get original image dimensions
                        im = PIL_Image.open(dest_img_path)
                        backup_img_to_write.width, backup_img_to_write.height = im.size
                        del im

                self.deal_with_images(where, how, image_to_write, instead_image)

                if (counter % 100) == 0:
                    where.db_writer.persist()
                    call_every_chunk()

        return row_count_for_csv

    def filter_unused_fields(self, custom_mapping, field_list: set) -> set:
        """
            Sanitize field list by removing the ones which are not known in mapping, nor used programmatically.
            :param custom_mapping:
            :param field_list:
            :return:
        """
        ok_fields = set([field for field in field_list
                         if field in custom_mapping.all_fields
                         or field in GlobalMapping.PredefinedFields
                         or field in self.ProgFields])
        ko_fields = [field for field in field_list if field not in ok_fields]
        if len(ko_fields) > 0:
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
        for alias, parent_class in GlobalMapping.parent_classes.items():
            dict_to_write = dicts_to_write[alias]
            ids_for_obj = existing_ids[alias]
            # Here we take advantage from consistent naming conventions
            # The 3 involved tables have "orig_id" column serving the same purpose
            parent_orig_id = dict_to_write.get("orig_id")
            if parent_orig_id is None:
                continue
            fk_to_obj = parent_class.pk()
            if dict_to_write.get("orig_id") in ids_for_obj:
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

    def filter_not_in_db_fields(self, custom_mapping: ProjectMapping, field_set: set,
                                target_fields) -> set:
        """
            Sanitize (more) field list by removing the ones which cannot be output into
            a DB table.
        :param custom_mapping:
        :param field_set:
        :param target_fields: The used field, by target table.
        :return:
        """
        ok_fields = set()
        ko_fields = []
        for a_field in field_set - self.ProgFields:
            mapping = GlobalMapping.PredefinedFields.get(a_field)
            if not mapping:
                mapping = custom_mapping.search_field(a_field)
            target_tbl = mapping["table"]
            target_fld = mapping["field"]
            target_class = GlobalMapping.target_classes[target_tbl]
            try:
                _target_col = getattr(target_class, target_fld)
                # TODO: col must be a Column, not, e.g. a relationship
                target_fields[target_tbl].add(target_fld)
            except AttributeError:
                ko_fields.append(a_field)
                continue
            ok_fields.add(a_field)
        if len(ko_fields) > 0:
            logger.warning("In %s, field(s) %s not known from DB, values will be ignored",
                           self.relative_name, ko_fields)
        return ok_fields

    @staticmethod
    def read_fields_to_dicts(how: ImportHow, field_set, lig, dicts_to_write, vals_cache: Dict):
        predefined_mapping = GlobalMapping.PredefinedFields
        custom_mapping = how.custom_mapping
        for a_field in field_set:
            # CSV reader returns a minimal dict with no value equal to None
            # TODO: below could be replaced with an intersect() of field names. To benchmark.
            if a_field not in lig:
                continue
            # We have a value
            raw_val = lig.get(a_field)
            # Try to get the value from the cache
            cache_key = (a_field, raw_val)
            cached_field_value = vals_cache.get(cache_key)
            m = predefined_mapping.get(a_field)
            if not m:
                m = custom_mapping.search_field(a_field)
            field_table = m.get("table")
            field_name = m.get("field")
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
                    # no caching of this one
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
            # TODO: sanitize mappings and forget this .get
            dict_to_write = dicts_to_write.get(field_table)
            if dict_to_write is not None:
                dict_to_write[field_name] = cached_field_value
            else:
                logger.info("skip T %s %s %s", field_table, field_name, cached_field_value)

    @staticmethod
    def create_or_link_slaves(prj_id, existing_objects, object_fields_to_write,
                              object_head_to_write) -> bool:
        # It can be a line with a complementary image
        if object_fields_to_write.orig_id in existing_objects:
            logger.info("Second image for %s ", object_fields_to_write.orig_id)
            # In this case just point to previous
            # TODO: It looks useless, anyway in original code the object is not added into session
            # object_head_to_write.objid = existing_objects[object_fields_to_write.orig_id]
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

        img_path, ndx_in_vault_folder, vault_folder, vault_folder_path = self.store_into_vault(where.vault,
                                                                                               img_file_path,
                                                                                               image_to_write)

        im = PIL_Image.open(img_path)
        image_to_write.width = im.size[0]
        image_to_write.height = im.size[1]
        # Generate a thumbnail if image is too large
        if (im.size[0] > how.max_dim) or (im.size[1] > how.max_dim):
            # We force thumbnail format to JPEG
            vault_thumb_filename = "%s_mini%s" % (ndx_in_vault_folder, '.jpg')
            # TODO: Doesn't it affect aspect ratio?
            im.thumbnail((how.max_dim, how.max_dim))
            if im.mode == 'P':
                im = im.convert("RGB")
            thumb_path: str = vault_folder_path.joinpath(vault_thumb_filename).as_posix()
            im.save(thumb_path)
            image_to_write.thumb_file_name = "%s/%s" % (vault_folder, vault_thumb_filename)
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
        if image_to_write.imgrank is None:
            image_to_write.imgrank = 0  # default value

    @staticmethod
    def store_into_vault(vault, img_file_path, image_to_write):
        assert image_to_write.imgid is not None
        # Images are stored in folders of 10K images max
        vault_folder = "%04d" % (image_to_write.imgid // 10000)
        ndx_in_vault_folder = "%04d" % (image_to_write.imgid % 10000)
        vault_folder_path: PurePath = vault.sub_path(vault_folder)
        # We store in DB line the path relative to vault
        vault_filename = "%s%s" % (ndx_in_vault_folder, img_file_path.suffix)
        vault_subpath = "%s/%s" % (vault_folder, vault_filename)
        image_to_write.file_name = vault_subpath
        vault.ensure_exists(vault_folder)
        # Copy image file from unzip directory to vault
        dest_img_path: str = vault_folder_path.joinpath(vault_filename).as_posix()
        # TODO: Move if on same filesystem
        # TODO: OS copy otherwise, 3x less time
        shutil.copyfile(img_file_path.as_posix(), dest_img_path)
        return dest_img_path, ndx_in_vault_folder, vault_folder, vault_folder_path

    def do_validate(self, how: ImportHow, diag: ImportDiagnostic):
        with open(self.path.as_posix(), encoding='latin_1') as csv_file:
            # Read as a dict, first line gives the format
            rdr = csv.DictReader(csv_file, delimiter='\t', quotechar='"')
            # Read types line (2nd line in file)
            type_line = {field.strip(" \t").lower(): v for field, v in rdr.__next__().items()}
            # Cleanup field names, keeping original ones as key
            clean_fields = {field: field.strip(" \t").lower() for field in rdr.fieldnames}
            # Extract field list from header cooked by CSV reader
            field_list = [clean_fields[field] for field in rdr.fieldnames]
            #
            self.validate_structure(how, diag, field_list, type_line)
            rows_for_csv = self.validate_content(how, diag, rdr, clean_fields)
            return rows_for_csv

    def validate_structure(self, how: ImportHow, diag: ImportDiagnostic, field_list, type_line):
        a_field: str
        for a_field in field_list:
            # split at first _ as the column name might contain an _
            split_col = a_field.split("_", 1)
            if len(split_col) != 2:
                diag.warn("Invalid Header '%s' in file %s. Format must be Table_Field. Field ignored"
                          % (a_field, self.relative_name))
                continue
            if a_field in GlobalMapping.PredefinedFields:
                # OK it's a predefined one
                continue
            if a_field in TSVFile.ProgFields:
                # Not mapped, but not a free field
                continue
            # Not a predefined field, so nXX or tXX
            if how.custom_mapping.search_field(a_field):
                # Custom field was already mapped, in a previous import or another TSV of present import
                continue
            # e.g. acq_sn -> acq
            tsv_table_prfx = split_col[0]
            # e.g. acq -> acquisitions
            target_table = GlobalMapping.TSV_table_to_table(tsv_table_prfx)
            if target_table not in GlobalMapping.PossibleTables:
                diag.warn("Invalid Header '%s' in file %s. Unknown table prefix. Field ignored"
                          % (a_field, self.relative_name))
                continue
            if target_table not in ('obj_head', 'obj_field'):
                # In other tables, all types are forced to text
                sel_type = 't'
                # TODO: Tell the user that an eventual type is just ignored
            else:
                sel_type = GlobalMapping.PossibleTypes.get(type_line[a_field])
                if sel_type is None:
                    diag.warn("Invalid Type '%s' for Field '%s' in file %s. "
                              "Incorrect Type. Field ignored"
                              % (type_line[a_field], a_field, self.relative_name))
                    continue
            # Add the new custom column
            target_col = split_col[1]
            how.custom_mapping.add_column(target_table, tsv_table_prfx, target_col, sel_type)
            logger.info("New field %s found in file %s", a_field, self.relative_name)
            # Warn that project settings were extended, i.e. empty columns
            if not how.custom_mapping.was_empty:
                diag.warn("New field %s found in file %s" % (a_field, self.relative_name))

    def validate_content(self, how: ImportHow, diag: ImportDiagnostic, rdr, clean_fields):
        row_count_for_csv = 0
        vals_cache = {}
        for lig in rdr:
            row_count_for_csv += 1

            self.validate_line(how, diag, lig, clean_fields, vals_cache)

            # Verify the image file
            object_id = clean_value_and_none(lig.get('object_id', ''))
            if object_id == '':
                diag.warn("Missing object_id in line '%s' of file %s. "
                          % (row_count_for_csv, self.relative_name))
            img_file_name = clean_value_and_none(lig.get('img_file_name', 'MissingField img_file_name'))
            # Below works as well for UVPV6, as the file 'name' is in fact a relative path,
            # e.g. 'sub1/20200205-111823_3.png'
            img_file_path = self.path.parent / img_file_name
            if not img_file_path.exists():
                diag.warn("Missing Image '%s' in file %s. "
                          % (img_file_name, self.relative_name))
            else:
                # noinspection PyBroadException
                try:
                    _im = PIL_Image.open(img_file_path.as_posix())
                except Exception as _e:
                    diag.warn("Error while reading Image '%s' in file %s. %s"
                              % (img_file_name, self.relative_name, sys.exc_info()[0]))

            # Verify duplicate images
            key_exist_obj = "%s*%s" % (object_id, img_file_name)
            if not how.skip_object_duplicates and key_exist_obj in diag.existing_objects_and_image:
                diag.warn("Duplicate object %s Image '%s' in file %s. "
                          % (object_id, img_file_name, self.relative_name))
            diag.existing_objects_and_image.add(key_exist_obj)

        return row_count_for_csv

    def validate_line(self, how: ImportHow, diag: ImportDiagnostic, lig, clean_fields, vals_cache):
        latitude_was_seen = False
        for raw_field, a_field in clean_fields.items():
            m = GlobalMapping.PredefinedFields.get(a_field)
            if m is None:
                m = how.custom_mapping.search_field(a_field)
                # No mapping, not stored
                if m is None:
                    continue
            raw_val = lig.get(raw_field)
            # Try to get the value from the cache
            cache_key = (raw_field, raw_val)
            if cache_key in vals_cache:
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
                latitude_was_seen = True
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf < -90 or vf > 90:
                    diag.warn("Invalid Lat. value '%s' for Field '%s' in file %s. "
                              "Incorrect range -90/+90°."
                              % (csv_val, raw_field, self.relative_name))
            elif a_field == 'object_lon':
                vf = convert_degree_minute_float_to_decimal_degree(csv_val)
                if vf < -180 or vf > 180:
                    diag.warn("Invalid Long. value '%s' for Field '%s' in file %s. "
                              "Incorrect range -180/+180°."
                              % (csv_val, raw_field, self.relative_name))
            elif m['type'] == 'n':
                vf = to_float(csv_val)
                if vf is None:
                    diag.warn("Invalid float value '%s' for Field '%s' in file %s."
                              % (csv_val, raw_field, self.relative_name))
                elif a_field == 'object_annotation_category_id':
                    diag.classif_id_seen.add(int(csv_val))
            elif a_field == 'object_date':
                try:
                    datetime.date(int(csv_val[0:4]), int(csv_val[4:6]), int(csv_val[6:8]))
                except ValueError:
                    diag.warn("Invalid Date value '%s' for Field '%s' in file %s."
                              % (csv_val, raw_field, self.relative_name))
            elif a_field == 'object_time':
                try:
                    csv_val = csv_val.zfill(6)
                    datetime.time(int(csv_val[0:2]), int(csv_val[2:4]), int(csv_val[4:6]))
                except ValueError:
                    diag.warn("Invalid Time value '%s' for Field '%s' in file %s."
                              % (csv_val, raw_field, self.relative_name))
            elif a_field == 'object_annotation_category':
                if clean_value_and_none(lig.get('object_annotation_category_id', '')) == '':
                    # Apply the mapping
                    csv_val = how.taxo_mapping.get(csv_val.lower(), csv_val)
                    # Record that the taxo was seen
                    how.taxo_found[csv_val.lower()] = None
            elif a_field == 'object_annotation_person_name':
                maybe_email = clean_value_and_none(lig.get('object_annotation_person_email', ''))
                # TODO: It's more "diag" than "how"
                how.found_users[csv_val.lower()] = {'email': maybe_email}
            elif a_field == 'object_annotation_status':
                if csv_val != 'noid' and csv_val.lower() not in classif_qual_revert:
                    diag.warn("Invalid Annotation Status '%s' for Field '%s' in file %s."
                              % (csv_val, raw_field, self.relative_name))
        # Update missing GPS count
        if not latitude_was_seen:
            diag.nb_objects_without_gps += 1
