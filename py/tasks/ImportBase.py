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
from typing import Union

from BO.Mappings import ProjectMapping
from db.Acquisition import Acquisition
from db.Image import Image
from db.Object import Object, ObjectFields
from db.Process import Process
from db.Project import Project
from db.Sample import Sample
from db.Task import Task
from db.Taxonomy import Taxonomy
from framework.Service import Service
from fs.TempTaskDir import TempTaskDir
from fs.Vault import Vault


# noinspection PyProtectedMember


class ImportBase(Service):
    """
        Common methods and data for import task steps.
    """
    PredefinedFields = {
        # A mapping from TSV columns to objects and fields
        'object_id': {'table': ObjectFields.__tablename__, 'field': 'orig_id', 'type': 't'},
        'sample_id': {'table': Sample.__tablename__, 'field': 'orig_id', 'type': 't'},
        'acq_id': {'table': Acquisition.__tablename__, 'field': 'orig_id', 'type': 't'},
        'process_id': {'table': Process.__tablename__, 'field': 'orig_id', 'type': 't'},
        'object_lat': {'table': Object.__tablename__, 'field': 'latitude', 'type': 'n'},
        'object_lon': {'table': Object.__tablename__, 'field': 'longitude', 'type': 'n'},
        'object_date': {'table': Object.__tablename__, 'field': 'objdate', 'type': 't'},
        'object_time': {'table': Object.__tablename__, 'field': 'objtime', 'type': 't'},
        'object_link': {'table': ObjectFields.__tablename__, 'field': 'object_link', 'type': 't'},
        'object_depth_min': {'table': Object.__tablename__, 'field': 'depth_min', 'type': 'n'},
        'object_depth_max': {'table': Object.__tablename__, 'field': 'depth_max', 'type': 'n'},
        'object_annotation_category': {'table': Object.__tablename__, 'field': 'classif_id', 'type': 't'},
        'object_annotation_category_id': {'table': Object.__tablename__, 'field': 'classif_id', 'type': 'n'},
        'object_annotation_date': {'table': Object.__tablename__, 'field': 'classif_when', 'type': 't'},
        'object_annotation_person_name': {'table': Object.__tablename__, 'field': 'classif_who', 'type': 't'},
        'object_annotation_status': {'table': Object.__tablename__, 'field': 'classif_qual', 'type': 't'},
        'img_rank': {'table': Image.__tablename__, 'field': 'imgrank', 'type': 'n'},
        'img_file_name': {'table': Image.__tablename__, 'field': 'orig_file_name', 'type': 't'},
        'sample_dataportal_descriptor': {'table': Sample.__tablename__, 'field': 'dataportal_descriptor', 'type': 't'},
        'acq_instrument': {'table': Acquisition.__tablename__, 'field': 'instrument', 'type': 't'},
    }

    # C'est un set de table 😁
    PossibleTables = set([v['table'] for v in PredefinedFields.values()])

    parent_classes = {Acquisition.__tablename__: Acquisition,
                      Sample.__tablename__: Sample,
                      Process.__tablename__: Process}

    target_classes = {**parent_classes,
                      Object.__tablename__: Object,
                      ObjectFields.__tablename__: ObjectFields,
                      Image.__tablename__: Image}

    # Fields which are not mapped, i.e. not directly destined to DB, but needed by Import for fallback
    ProgFields = {'object_annotation_time',
                  'object_annotation_person_email',
                  # 'annotation_person_first_name' # historical
                  }

    # (f)loat->(n)umerical
    PossibleTypes = {'[f]': 'n', '[t]': 't'}

    def __init__(self):
        super().__init__()
        # From legacy code, vault and temptask are in src directory
        self.vault = Vault(join(self.link_src, 'vault'))
        self.temptask = TempTaskDir(join(self.link_src, 'temptask'))
        # Parameters
        self.prj_id: int = -1
        self.task_id: int = -1
        self.custom_mapping: Union[ProjectMapping, None] = None
        self.taxo_mapping: dict = self.PredefinedFields
        self.taxo_found = {}
        self.found_users = {}
        self.skip_object_duplicate: str = "N"
        self.skip_already_loaded_file: str = "N"
        self.ignore_duplicates: str = "N"
        self.source_dir_or_zip: str = ""
        # Work vars
        self.prj: Union[Project, None] = None
        self.task: Union[Task, None] = None

    @staticmethod
    def possible_tsv_files(source_dir):
        """
            Return the TSV files we have to process. Generator function to save mem...
        """
        for a_filter in ("**/ecotaxa*.txt", "**/ecotaxa*.tsv", "**/*Images.zip"):
            for a_csv_file in source_dir.glob(a_filter):
                yield a_csv_file

    def fetch_existing_images(self):
        # This is only necessary if we must ignore duplicates
        if self.ignore_duplicates == 'Y':
            return Image.fetch_existing_images(self.session, self.prj_id)
        else:
            return set()

    def update_param(self):
        if hasattr(self, 'param'):
            self.task.inputparam = json.dumps(self.param.__dict__)
        self.task.lastupdate = datetime.datetime.now()
        self.session.commit()

    def update_progress(self, percent: int, message: str):
        self.task.progresspct = percent
        self.task.progressmsg = message
        self.update_param()

    @staticmethod
    def log_for_user(msg: str):
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

        Taxonomy.fetch_taxons(self.session, taxo_found, lower_taxon_list)

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

    def handle_uvpapp_format(self, csv_file, relative_name):
        was_uvpv6 = False
        # TODO: Use FS and a BO
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
            was_uvpv6 = True
        return csv_file, was_uvpv6

    def prepare_run(self):
        """
            Load what's needed for run.
        """
        self.prj = self.session.query(Project).filter_by(projid=self.prj_id).first()
        self.task = self.session.query(Task).filter_by(id=self.task_id).first()
