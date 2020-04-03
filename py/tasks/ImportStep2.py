# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import configparser
import csv
import datetime
import json
import logging
import random
import shutil
import time
from pathlib import Path, PurePath
from typing import Dict

# noinspection PyPackageRequirements
from PIL import Image as PIL_Image

from BO.Mappings import ProjectMapping
from BO.Vignette import VignetteMaker
from db.Image import Image
from db.Object import classif_qual_revert, Object
from db.Project import Project
from utils import clean_value, to_float, none_to_empty, calc_astral_day_time, \
    convert_degree_minute_float_to_decimal_degree
from .DBWriter import DBWriter
from .ImportBase import ImportBase


class ImportStep2(ImportBase):

    def __init__(self, json_params: str):
        super(ImportStep2, self).__init__()
        # Received from parameters
        params = json.loads(json_params)
        # TODO a clean interface
        self.prj_id = params["prj"]
        self.task_id = params["tsk"]
        self.source_dir_or_zip = params["src"]
        self.custom_mapping = ProjectMapping().load_from_dict(params["map"])
        # The row count seen at previous step
        self.total_row_count = 0

    def run(self):
        """
            Do the real job using injected parameters.
        :return:
        """
        super(ImportStep2, self).prepare_run()
        loaded_files = none_to_empty(self.prj.fileloaded).splitlines()
        logging.info("loaded_files = %s", loaded_files)
        self.save_mapping()
        existing_parent_ids = self.fetch_existing_parent_ids()
        # The created objects (unicity from object_id in TSV, orig_id in model)
        existing_objects: set = self.fetch_existing_objects()
        existing_objects_and_image: set = self.fetch_existing_images()
        logging.info("existing_parent_ids = %s", existing_parent_ids)
        random.seed()
        source_dir = Path(self.source_dir_or_zip)
        total_row_count = 0
        db_writer = DBWriter(self.session)
        start_time = time.time()
        for a_csv_file in self.possible_tsv_files(source_dir):
            relative_file = a_csv_file.relative_to(source_dir)
            # relative name for logging and recording what was done
            relative_name: str = relative_file.as_posix()
            if relative_name in loaded_files and self.skip_already_loaded_file == 'Y':
                logging.info("File %s skipped, already loaded" % relative_name)
                continue
            logging.info("Analyzing file %s" % relative_name)

            a_csv_file, was_uvpv6 = self.handle_uvpapp_format(a_csv_file, relative_file)

            vignette_maker = False
            if was_uvpv6:
                # Pick vignette-ing config file from the zipped directory
                potential_config = a_csv_file.parent / "compute_vignette.txt"
                if potential_config.exists():
                    vignette_maker_cfg = configparser.ConfigParser()
                    vignette_maker_cfg.read(potential_config.as_posix())
                    vignette_maker = VignetteMaker(vignette_maker_cfg)

            with open(a_csv_file.as_posix(), encoding='latin_1') as csvfile:
                # Read as a dict, first line gives the format
                rdr = csv.DictReader(csvfile, delimiter='\t', quotechar='"')
                # Read types line (2nd line in file). This line is ignored.
                _type_line = {field: v for field, v in rdr.__next__().items()}
                # Cleanup field names, keeping original ones as key
                clean_fields = {field: field.strip(" \t").lower() for field in rdr.fieldnames}
                # Extract field list from header cooked by CSV reader
                field_set = set([clean_fields[field] for field in rdr.fieldnames])
                # Only keep the fields we can persist
                field_set = self.filter_unused_fields(field_set, relative_name)

                # Remove fields which are unknown in ORM
                target_fields = {alias: set() for alias in self.target_classes.keys()}
                field_set = self.filter_not_in_db_fields(field_set, relative_name, target_fields)

                # We can now prepare ORM classes with optimal performance
                ObjectGen, ObjectFieldsGen, ImageGen = db_writer.generators(target_fields)

                # For annotation, if there is both an id and a category then ignore category
                ignore_annotation_category: bool = 'object_annotation_category_id' in field_set \
                                                   and 'object_annotation_category' in field_set

                vals_cache = dict()
                # Loop over all lines
                row_count_for_csv = 0
                for rawlig in rdr:
                    # Bean counting
                    row_count_for_csv += 1
                    total_row_count += 1

                    lig = {clean_fields[field]: v for field, v in rawlig.items()}

                    # ------------- extract method do_one_tsv_line from here

                    # First read into dicts, faster than doing settattr()
                    dicts_to_write = {alias: dict() for alias in self.target_classes.keys()}

                    if ignore_annotation_category:
                        # Remove category as required, but only if there is really an id value
                        # it can happen that the id is empty, even if table header is present
                        if clean_value(lig.get('object_annotation_category_id', '')) != '':
                            del lig['object_annotation_category']

                    # Read TSV line into dicts
                    self.read_fields_to_dicts(field_set, lig, dicts_to_write, vals_cache)

                    # Create SQLAlchemy mappers of the object itself and slaves (1<->1)
                    object_head_to_write = ObjectGen(**dicts_to_write["obj_head"])
                    object_fields_to_write = ObjectFieldsGen(**dicts_to_write["obj_field"])
                    image_to_write = ImageGen(**dicts_to_write["images"])
                    # Parents are created the same way, _when needed_ (i.e. nearly never),
                    #  in @see add_parent_objects

                    object_head_to_write.sunpos = self.compute_sun_position(object_head_to_write)

                    self.add_parent_objects(existing_parent_ids, object_head_to_write, dicts_to_write)

                    key_exist_obj = "%s*%s" % (object_fields_to_write.orig_id, image_to_write.orig_file_name)
                    if self.skip_object_duplicate == 'Y' and key_exist_obj in existing_objects_and_image:
                        logging.info("***************** Continue")
                        continue

                    must_write_obj = self.create_or_link_slaves(db_writer, existing_objects, object_fields_to_write,
                                                                object_head_to_write)

                    db_writer.add_db_entities(object_head_to_write, object_fields_to_write, image_to_write,
                                              must_write_obj)

                    existing_objects.add(object_fields_to_write.orig_id)

                    img_file_path_from_tsv = a_csv_file.parent / image_to_write.orig_file_name

                    if vignette_maker:
                        # If there is need for a vignette, the file named in the TSV is NOT the one written,
                        # and pointed at, by the usual DB line. Instead, it's the vignette.
                        # We generate the vignette into temporary work directory
                        # TODO: Dup code, temptask dir is constant over service life
                        img_file_path = self.temptask.base_dir_for(self.task_id) / "tempvignette.png"
                        vignette_maker.make_vignette(img_file_path_from_tsv, img_file_path)

                    self.deal_with_images(a_csv_file, was_uvpv6, vignette_maker, image_to_write)

                    if vignette_maker and vignette_maker.must_keep_original():
                        # In this case, the original image is kept in another DB line
                        backup_img_to_write = ImageGen(**dicts_to_write["images"])
                        backup_img_to_write.imgrank = 100
                        backup_img_to_write.thumb_file_name = None
                        backup_img_to_write.thumb_width = None
                        backup_img_to_write.thumb_height = None
                        db_writer.add_vignette_backup(object_head_to_write, backup_img_to_write)
                        # Store original image
                        dest_img_path, _dummy1, _dummy1, _dummy1 = self.store_into_vault(img_file_path_from_tsv,
                                                                                         backup_img_to_write)
                        # Get original image dimensions
                        im = PIL_Image.open(dest_img_path)
                        backup_img_to_write.width, backup_img_to_write.height = im.size
                        del im

                    db_writer.close_row()

                    # ------------- to here
                    if (total_row_count % 100) == 0:
                        db_writer.persist()
                        # TODO
                        # self.UpdateProgress(100 * total_row_count / self.param.TotalRowCount,
                        #                     "Processing files %d/%d" % (total_row_count, self.total_row_count))

                db_writer.persist()
                # Bean counting continues
                elapsed = time.time() - start_time
                rows_per_sec = int(total_row_count / elapsed)
                logging.info("File %s : %d rows loaded, %d so far at %d rows/s",
                             relative_name, row_count_for_csv, total_row_count,
                             rows_per_sec)

                loaded_files.append(relative_name)
                self.prj.fileloaded = "\n".join(loaded_files)

                db_writer.eof_cleanup()

                # TODO: Just for tests
                # if total_row_count > 10000:
                #    break
        # Ensure the ORM has no shadow copy before going to plain SQL
        self.session.expunge_all()
        # TODO: Move to right DB classes
        self.update_counts_and_img0()
        self.propagate_geo()
        logging.info("Total of %d rows loaded" % total_row_count)
        Project.update_taxo_stats(self.session, self.prj_id)
        # Stats depend on taxo stats
        Project.update_stats(self.session, self.prj_id)

    def filter_unused_fields(self, field_list: set, relative_name) -> set:
        """
            Sanitize field list by removing the ones which are not known in mapping, nor used programmatically.
        :param field_list:
        :param relative_name:
        :return:
        """
        ok_fields = set([field for field in field_list
                         if field in self.custom_mapping.all_fields
                         or field in self.PredefinedFields
                         or field in self.ProgFields])
        ko_fields = [field for field in field_list if field not in ok_fields]
        if len(ko_fields) > 0:
            logging.warning("In %s, field(s) %s not used, values will be ignored",
                            relative_name, ko_fields)
        return ok_fields

    def filter_not_in_db_fields(self, field_set: set, relative_name, target_fields) -> set:
        """
            Sanitize (more) field list by removing the ones which cannot be output into
            a DB table.
        :param field_set:
        :param relative_name:
        :param target_fields: The used field, by target table.
        :return:
        """
        ok_fields = set()
        ko_fields = []
        for a_field in field_set - self.ProgFields:
            mapping = self.PredefinedFields.get(a_field)
            if not mapping:
                mapping = self.custom_mapping.search_field(a_field)
            target_tbl = mapping["table"]
            target_fld = mapping["field"]
            target_class = self.target_classes[target_tbl]
            try:
                _target_col = getattr(target_class, target_fld)
                # TODO: col must be a Column, not, e.g. a relationship
                target_fields[target_tbl].add(target_fld)
            except AttributeError:
                ko_fields.append(a_field)
                continue
            ok_fields.add(a_field)
        if len(ko_fields) > 0:
            logging.warning("In %s, field(s) %s not known from DB, values will be ignored",
                            relative_name, ko_fields)
        return ok_fields

    def create_or_link_slaves(self, db_writer, existing_objects, object_fields_to_write, object_head_to_write) -> bool:
        # It can be a line with a complementary image
        if object_fields_to_write.orig_id in existing_objects:
            logging.info("Second image for %s ", object_fields_to_write.orig_id)
            # In this case just point to previous
            # TODO: It looks useless, anyway in original code the object is not added into session
            # object_head_to_write.objid = existing_objects[object_fields_to_write.orig_id]
            return False
        else:
            # or create it
            object_head_to_write.projid = self.prj_id
            object_head_to_write.random_value = random.randint(1, 99999999)
            # Below left NULL @see self.update_counts_and_img0
            # object_head_to_write.img0id = XXXXX
            db_writer.link(object_fields_to_write, object_head_to_write)
            return True

    astral_cache = {'date': None, 'time': None, 'long': None, 'lat': None, 'r': ''}

    @staticmethod
    def compute_sun_position(object_head_to_write):
        # Compute sun position if not already done
        cache = ImportStep2.astral_cache
        if not (cache['date'] == object_head_to_write.objdate
                and cache['time'] == object_head_to_write.objtime
                and cache['long'] == object_head_to_write.longitude
                and cache['lat'] == object_head_to_write.latitude):
            ImportStep2.astral_cache = {'date': object_head_to_write.objdate,
                                        'time': object_head_to_write.objtime,
                                        'long': object_head_to_write.longitude,
                                        'lat': object_head_to_write.latitude,
                                        'r': ''}
            cache = ImportStep2.astral_cache
            try:
                cache['r'] = calc_astral_day_time(cache['date'],
                                                  cache['time'],
                                                  cache['lat'],
                                                  cache['long'])
            except Exception as e:
                # autre erreurs par exemple si l'heure n'est pas valide;
                logging.error("Astral error : %s for %s", e, cache)
        return cache['r']

    def read_fields_to_dicts(self, field_set, lig, dicts_to_write, vals_cache: Dict):
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
            m = self.PredefinedFields.get(a_field)
            if not m:
                m = self.custom_mapping.search_field(a_field)
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
                    # numeric version is in "if type=n" case
                    csv_val = self.taxo_mapping.get(csv_val.lower(), csv_val)
                    # Use initial mapping
                    cached_field_value = self.taxo_found[none_to_empty(csv_val).lower()]
                elif field_name == 'classif_who':
                    # Eventually map to another user if asked so
                    cached_field_value = self.found_users[none_to_empty(csv_val).lower()].get('id', None)
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
                logging.info("skip T %s %s %s", field_table, field_name, cached_field_value)

    def add_parent_objects(self, existing_ids, object_head_to_write, dicts_to_write):
        """
            Assignment of Sample, Acquisition & Process ID, creating them if necessary
            Due to amount of duplicated information in TSV, this happens for few % of rows
             so no real need to optimize here.
        """
        for alias, parent_class in self.parent_classes.items():
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
                obj_to_write.projid = self.prj_id
                self.session.add(obj_to_write)
                self.session.flush()
                # We now have a (generated) PK to copy back into objects
                # TODO: Skip the getattr() below in favor of obj_to_write.pk_val()
                ids_for_obj[parent_orig_id] = getattr(obj_to_write, fk_to_obj)
                logging.info("++ IDS %s %s", alias, ids_for_obj)
            # Anyway
            setattr(object_head_to_write, fk_to_obj, ids_for_obj[parent_orig_id])

    def deal_with_images(self, a_csv_file: Path, was_uvpv6: bool, vignette_maker: VignetteMaker, image_to_write: Image):
        """
            Generate image, eventually the vignette, create DB line(s) and copy image file into vault.
        :param a_csv_file:
        :param image_to_write:
        :param was_uvpv6:
        :param vignette_maker:
        :return:
        """
        if vignette_maker:
            # Source file is the temporary vignette
            img_file_path = self.temptask.base_dir_for(self.task_id) / "tempvignette.png"
        elif was_uvpv6:
            # Files are in a subdirectory for UVPV6
            img_file_path = a_csv_file.parent.joinpath(image_to_write.orig_file_name)
        else:
            # As per zip files structure, image files are in same directory as their description
            img_file_path = a_csv_file.with_name(image_to_write.orig_file_name)

        img_path, ndx_in_vault_folder, vault_folder, vault_folder_path = self.store_into_vault(img_file_path,
                                                                                               image_to_write)

        im = PIL_Image.open(img_path)
        image_to_write.width = im.size[0]
        image_to_write.height = im.size[1]
        size_limit = int(self.config['THUMBSIZELIMIT'])
        # Generate a thumbnail if image is too large
        if (im.size[0] > size_limit) or (im.size[1] > size_limit):
            # We force thumbnail format to JPEG
            vault_thumb_filename = "%s_mini%s" % (ndx_in_vault_folder, '.jpg')
            # TODO: Doesn't it affect aspect ratio?
            im.thumbnail((size_limit, size_limit))
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

    def store_into_vault(self, img_file_path, image_to_write):
        assert image_to_write.imgid is not None
        # Images are stored in folders of 10K images max
        vault_folder = "%04d" % (image_to_write.imgid // 10000)
        ndx_in_vault_folder = "%04d" % (image_to_write.imgid % 10000)
        vault_folder_path: PurePath = self.vault.sub_path(vault_folder)
        # We store in DB line the path relative to vault
        vault_filename = "%s%s" % (ndx_in_vault_folder, img_file_path.suffix)
        vault_subpath = "%s/%s" % (vault_folder, vault_filename)
        image_to_write.file_name = vault_subpath
        self.vault.ensure_exists(vault_folder)
        # Copy image file from unzip directory to vault
        dest_img_path: str = vault_folder_path.joinpath(vault_filename).as_posix()
        # TODO: Move if on same filesystem
        # TODO: OS copy otherwise, 3x less time
        shutil.copyfile(img_file_path.as_posix(), dest_img_path)
        return dest_img_path, ndx_in_vault_folder, vault_folder, vault_folder_path

    def update_counts_and_img0(self):
        # noinspection SqlRedundantOrderingDirection
        self.session.execute("""
        UPDATE obj_head o
           SET imgcount = (SELECT count(*) FROM images WHERE objid = o.objid),
               img0id = (SELECT imgid FROM images WHERE objid = o.objid ORDER BY imgrank ASC LIMIT 1)
         WHERE projid = :prj
           AND (imgcount IS NULL or img0id IS NULL) """,
                             {'prj': self.prj_id})
        self.session.commit()

    def propagate_geo(self):
        """
            Create sample geo from object one.
        :return:
        """
        self.session.execute("""
        UPDATE samples s 
           SET latitude = sll.latitude, longitude = sll.longitude
          FROM (SELECT o.sampleid, min(o.latitude) latitude, min(o.longitude) longitude
                  FROM obj_head o
                 WHERE projid = :projid 
                   AND o.latitude IS NOT NULL 
                   AND o.longitude IS NOT NULL
              GROUP BY o.sampleid) sll 
         WHERE s.sampleid = sll.sampleid 
           AND projid = :projid """,
                             {'projid': self.prj_id})
        self.session.commit()

    def fetch_existing_objects(self):
        # Get existing object IDs (orig_id AKA object_id in TSV) from the project
        return Object.fetch_existing_objects(self.session, self.prj_id)

    def fetch_existing_parent_ids(self):
        """
        Get from DB the present IDs for the tables we are going to update, in current project.
        :return:
        """
        existing_ids = {}
        # Get orig_id from acquisition, sample, process
        for alias, clazz in self.parent_classes.items():
            collect = clazz.get_orig_id_and_pk(self.session, self.prj_id)
            existing_ids[alias] = collect
        return existing_ids

    def save_mapping(self):
        """
        DB update of mappings for the Project
        """
        self.custom_mapping.write_to_project(self.prj)
        self.session.commit()
