# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
import json
import logging
import re
import shutil
import zipfile
from os.path import join

# noinspection PyProtectedMember
from sqlalchemy.engine import ResultProxy

from db.Acquisition import Acquisition
from db.Image import Image
from db.Object import Object, ObjectFields
from db.Process import Process
from db.Project import Project
from db.Sample import Sample
from db.Task import Task
from framework.Service import Service
from fs.TempTaskDir import TempTaskDir
from fs.Vault import Vault


class ImportBase(Service):
    """
        Common methods and data for import task steps.
    """
    PredefinedFields = {
        # A mapping from TSV columns to objects and fields
        'object_id': {'table': 'obj_field', 'field': 'orig_id', 'type': 't'},
        'sample_id': {'table': 'sample', 'field': 'orig_id', 'type': 't'},
        'acq_id': {'table': 'acq', 'field': 'orig_id', 'type': 't'},
        'process_id': {'table': 'process', 'field': 'orig_id', 'type': 't'},
        'object_lat': {'table': 'obj_head', 'field': 'latitude', 'type': 'n'},
        'object_lon': {'table': 'obj_head', 'field': 'longitude', 'type': 'n'},
        'object_date': {'table': 'obj_head', 'field': 'objdate', 'type': 't'},
        'object_time': {'table': 'obj_head', 'field': 'objtime', 'type': 't'},
        'object_link': {'table': 'obj_field', 'field': 'object_link', 'type': 't'},
        'object_depth_min': {'table': 'obj_head', 'field': 'depth_min', 'type': 'n'},
        'object_depth_max': {'table': 'obj_head', 'field': 'depth_max', 'type': 'n'},
        'object_annotation_category': {'table': 'obj_head', 'field': 'classif_id', 'type': 't'},
        'object_annotation_category_id': {'table': 'obj_head', 'field': 'classif_id', 'type': 'n'},
        'object_annotation_date': {'table': 'obj_head', 'field': 'classif_when', 'type': 't'},
        'object_annotation_person_name': {'table': 'obj_head', 'field': 'classif_who', 'type': 't'},
        'object_annotation_status': {'table': 'obj_head', 'field': 'classif_qual', 'type': 't'},
        'img_rank': {'table': 'image', 'field': 'imgrank', 'type': 'n'},
        'img_file_name': {'table': 'image', 'field': 'orig_file_name', 'type': 't'},
        'sample_dataportal_descriptor': {'table': 'sample', 'field': 'dataportal_descriptor', 'type': 't'},
        'acq_instrument': {'table': 'acq', 'field': 'instrument', 'type': 't'},
    }

    # Fields which are not mapped, i.e. not directly destined to DB, but needed by Import for fallback
    ProgFields = {'object_annotation_time',
                  'object_annotation_person_email',
                  # 'annotation_person_first_name' # historical
                  }

    # C'est un set de table 😁
    PossibleTables = set([v['table'] for v in PredefinedFields.values()])
    # (f)loat->(n)umerical
    PossibleTypes = {'[f]': 'n', '[t]': 't'}

    parent_pks = {"acq": Acquisition.acquisid.name, "sample": Sample.sampleid.name,
                  "process": Process.processid.name}
    parent_classes = {"acq": Acquisition, "sample": Sample,
                      "process": Process}
    target_classes = {**parent_classes,
                      "obj_head": Object, "obj_field": ObjectFields,
                      "image": Image}

    def __init__(self):
        super().__init__()
        # From legacy code, vault and temptask are in src directory
        self.vault = Vault(join(self.link_src, 'vault'))
        self.temptask = TempTaskDir(join(self.link_src, 'temptask'))
        # Parameters
        self.prj_id: int = -1
        self.task_id: int = -1
        self.mapping: dict = {}
        self.taxo_mapping: dict = self.PredefinedFields
        self.taxo_found = {}
        self.found_users = {}
        self.skip_object_duplicate: str = "N"
        self.skip_already_loaded_file: str = "N"
        self.ignore_duplicates: str = "N"
        self.source_dir_or_zip: str = ""
        # Work vars
        self.prj: Project = None
        self.task: Task = None

    @staticmethod
    def possible_tsv_files(source_dir):
        """
            Return the TSV files we have to process. Generator function to save mem...
        """
        for a_filter in ("**/ecotaxa*.txt", "**/ecotaxa*.tsv", "**/*Images.zip"):
            for a_csv_file in source_dir.glob(a_filter):
                yield a_csv_file

    def fetch_existing_images(self):
        # Get all object/image pairs from the project
        existing_objects_and_image = set()
        # This is only necessary if we must ignore duplicates
        if self.ignore_duplicates == 'Y':
            res: ResultProxy = self.session.execute(
                # Must be reloaded from DB, as phase 1 added all objects for duplicates checking
                "SELECT concat(o.orig_id,'*',i.orig_file_name) "
                "  FROM images i "
                "  JOIN objects o ON i.objid = o.objid "
                " WHERE o.projid= :prj",
                {"prj": self.prj_id})
            for rec in res:
                existing_objects_and_image.add(rec[0])
        return existing_objects_and_image

    def update_param(self):
        if hasattr(self, 'param'):
            self.task.inputparam = json.dumps(self.param.__dict__)
        self.task.lastupdate = datetime.datetime.now()
        self.session.commit()

    def update_progress(self, percent: int, message: str):
        self.task.progresspct = percent
        self.task.progressmsg = message
        self.update_param()

    def log_for_user(self, msg: str):
        # TODO
        print(msg)
        pass

    def resolve_taxo_found(self, taxo_found) -> [str]:
        lower_taxon_list = []
        not_found_taxo = []
        regexsearchparenthese = re.compile(r'(.+) \((.+)\)$')
        for lowertaxon in taxo_found.keys():
            taxo_found[lowertaxon] = {'nbr': 0, 'id': None}
            lower_taxon_list.append(lowertaxon)
            resregex = regexsearchparenthese.match(lowertaxon)
            if resregex:  # Si on trouve des parenthèse à la fin
                lowertaxonLT = resregex.group(1) + '<' + resregex.group(2)
                taxo_found[lowertaxon]['alterdisplayname'] = lowertaxonLT
                lower_taxon_list.append(lowertaxonLT)

        self.fetch_taxons(taxo_found, lower_taxon_list)

        logging.info("Taxo Found = %s", taxo_found)
        for FoundK, FoundV in taxo_found.items():
            if FoundV['nbr'] == 0:
                logging.info("Taxo '%s' Not Found", FoundK)
                not_found_taxo.append(FoundK)
            elif FoundV['nbr'] > 1:
                # more than one is like not found
                logging.info("Taxo '%s' Found more than once", FoundK)
                not_found_taxo.append(FoundK)
                taxo_found[FoundK]['id'] = None
        for FoundK, FoundV in taxo_found.items():
            # in the end we just keep the id, other fields were transitory
            taxo_found[FoundK] = FoundV['id']
        return not_found_taxo

    def fetch_taxons(self, taxo_found, taxon_lower_list):
        res: ResultProxy = self.session.execute(
            """SELECT t.id,lower(t.name) AS name, lower(t.display_name) display_name, 
                      lower(t.name)||'<'||lower(p.name) AS computedchevronname 
                FROM taxonomy t
                LEFT JOIN taxonomy p on t.parent_id=p.id
                WHERE lower(t.name) = ANY(:nms) OR lower(t.display_name) = ANY(:dms) 
                    OR lower(t.name)||'<'||lower(p.name) = ANY(:chv) """
            , {"nms": taxon_lower_list, "dms": taxon_lower_list, "chv": taxon_lower_list})
        for rec_taxon in res:
            for found_k, found_v in taxo_found.items():
                if ((found_k == rec_taxon['name'])
                        or (found_k == rec_taxon['display_name'])
                        or (found_k == rec_taxon['computedchevronname'])
                        or (('alterdisplayname' in found_v) and (
                                found_v['alterdisplayname'] == rec_taxon['display_name']))):
                    taxo_found[found_k]['nbr'] += 1
                taxo_found[found_k]['id'] = rec_taxon['id']

    def handle_uvpapp_format(self, csv_file, relative_name):
        if relative_name.name.endswith("Images.zip"):
            # It comes from UVPAPP, each sample is in a .zip
            sample_dir = self.temptask.base_dir_for(self.task_id) / relative_name.stem
            sample_csv = sample_dir / ("ecotaxa_" + relative_name.stem[:-7] + ".tsv")
            if sample_dir.exists():
                # target directory exists, maybe from a previous unzip?
                if not sample_csv.exists():
                    # incorrect unzipping
                    # sample_dir.rmdir() # on détruit le repertoire et on redezippe
                    shutil.rmtree(sample_dir.as_posix())
            if not sample_dir.exists():
                sample_dir.mkdir()
                with zipfile.ZipFile(csv_file.as_posix(), 'r') as z:
                    z.extractall(sample_dir.as_posix())
            csv_file = sample_csv
        return csv_file

    def prepare_run(self):
        """
            Load what's needed for run.
        """
        self.prj = self.session.query(Project).filter_by(projid=self.prj_id).first()
        self.task = self.session.query(Task).filter_by(id=self.task_id).first()
