# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from collections import OrderedDict

from db.Acquisition import Acquisition
from db.Image import Image
from db.Object import ObjectFields, Object
from db.Process import Process
from db.Project import Project
from db.Sample import Sample
from utils import encode_equal_list


class GlobalMapping(object):
    """
        Information about mapping process (from TSV to DB)
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

    # (f)loat->(n)umerical
    PossibleTypes = {'[f]': 'n', '[t]': 't'}
    # TSV prefix to 'real' table name, only for extendable tables
    PrefixToTable = {
        'object': ObjectFields.__tablename__,
        'acq': Acquisition.__tablename__,
        'process': Process.__tablename__,
        'sample': Sample.__tablename__,
    }
    TableToPrefix = {v: k for k, v in PrefixToTable.items()}

    @classmethod
    def TSV_table_to_table(cls, table):
        """
            Return the real table name behind the one uses in TSV composed column names.
        """
        return cls.PrefixToTable.get(table, table)


class ProjectMapping(object):
    """
        In some DB tables, free fields are present at the end of the table. Their names are constant
        e.g. n01 to n100.
        During import, some TSV _columns_ are mapped to free fields. The values in each line are then
        copied to DB columns of corresponding DB table line.
        In order to remember the original TSV column names, the mappings are stored at project level.
        So e.g. TSV column object_x become object_fields.n01 and we have an object mapping "n01=x"

        By convention, numerical columns have 'n' as first column name, text ones have 't'.

    """

    def __init__(self):
        self.object_mappings: TableMapping = TableMapping(ObjectFields.__tablename__)
        self.sample_mappings: TableMapping = TableMapping(Sample.__tablename__)
        self.acquisition_mappings: TableMapping = TableMapping(Acquisition.__tablename__)
        self.process_mappings: TableMapping = TableMapping(Process.__tablename__)
        # store for iteration
        self.all = [self.object_mappings, self.sample_mappings,
                    self.acquisition_mappings, self.process_mappings]
        # for 'generic' access to mappings
        self.by_table_name = {a_mapping.table: a_mapping for a_mapping in self.all}
        # for fast lookup from TSV analysis
        # key = TSV full column, val = ( TableMapping, DB col )
        self.all_fields = dict()

    def write_to_project(self, prj: Project):
        """
            Write the mappings into given Project .
        """
        prj.mappingobj = self.object_mappings.as_equal_list()
        prj.mappingsample = self.sample_mappings.as_equal_list()
        prj.mappingacq = self.acquisition_mappings.as_equal_list()
        prj.mappingprocess = self.process_mappings.as_equal_list()

    def load_from_project(self, prj: Project):
        """
            Load self from Project fields serialization.
        """
        self.object_mappings.load_from_equal_list(prj.mappingobj)
        self.sample_mappings.load_from_equal_list(prj.mappingsample)
        self.acquisition_mappings.load_from_equal_list(prj.mappingacq)
        self.process_mappings.load_from_equal_list(prj.mappingprocess)
        self.build_all_fields()
        return self

    def as_dict(self):
        """
            Return the mapping as a serializable object for messaging.
        """
        out_dict = {mapping.table: mapping.real_cols_to_tsv
                    for mapping in self.all}
        return out_dict

    def load_from_dict(self, in_dict: dict):
        """
            Use data produced by @as_dict previous for loading self.
        """
        for a_mapping in self.all:
            a_mapping.load_from_dict(in_dict[a_mapping.table])
        self.build_all_fields()
        return self

    def is_empty(self) -> bool:
        for a_mapping in self.all:
            if not a_mapping.is_empty():
                return False
        return True

    def add_column(self, target_table: str, tsv_table: str, tsv_field: str, sel_type):
        """
            A new custom column was found, add it into the right bucket.
        """
        for_table: TableMapping = self.by_table_name[target_table]
        for_table.add_column_for_table(tsv_field, sel_type)
        real_col = for_table.tsv_cols_to_real[tsv_field]
        self.all_fields["%s_%s" % (tsv_table, tsv_field)] = (for_table, real_col)

    def search_field(self, full_tsv_field: str):
        """
            Return the storage (i.e. target of mapping) for a custom field in given table.
        """
        mping = self.all_fields.get(full_tsv_field)
        if mping is None:
            return None
        (mping, real_col) = mping
        return {'table': mping.table, 'field': real_col, 'type': real_col[0]}

    def build_all_fields(self):
        """
            Build cache all_fields for lookup.
        """
        all_fields = {}
        for a_mapping in self.all:
            tbl = a_mapping.table
            prfx = GlobalMapping.TableToPrefix.get(tbl, tbl)
            for real_col, tsv_col in a_mapping.real_cols_to_tsv.items():
                all_fields["%s_%s" % (prfx, tsv_col)] = (a_mapping, real_col)
        self.all_fields = all_fields


class TableMapping(object):
    """
        The mapping for a given DB table, i.e. from TSV columns to DB ones.
    """

    def __init__(self, table: str):
        self.table = table
        # key = DB column, val = TSV field name WITHOUT table prefix
        self.real_cols_to_tsv = OrderedDict()
        # key = TSV field name WITHOUT table prefix, val = DB column
        self.tsv_cols_to_real = OrderedDict()
        self.max_by_type = {'n': 0, 't': 0}

    def load_from_equal_list(self, str_mapping: str):
        """
            Input has form, e.g.:
                n01=lat_end
                n02=lon_end
                n03=area
                ...
        """
        if not str_mapping:
            # None or "" => nothing to do
            return
        for a_map in str_mapping.splitlines():
            if not a_map:
                # Empty lines are tolerated
                continue
            db_col, tsv_col_no_prfx = a_map.split('=', 1)
            self.add_association(db_col, tsv_col_no_prfx)
        # TODO: Adjust max in the end only

    def load_from_dict(self, dict_mapping: dict):
        for db_col, tsv_col_no_prfx in dict_mapping.items():
            self.add_association(db_col, tsv_col_no_prfx)

    def add_association(self, db_col, tsv_col_no_prfx):
        self.real_cols_to_tsv[db_col] = tsv_col_no_prfx
        self.tsv_cols_to_real[tsv_col_no_prfx] = db_col
        self.adjust_max(db_col, self.max_by_type)

    @staticmethod
    def adjust_max(db_col, max_by_type):
        # Adjust maximum for type
        db_col_type = db_col[0]
        db_col_ndx = int(db_col[1:])
        if db_col_ndx > max_by_type[db_col_type]:
            max_by_type[db_col_type] = db_col_ndx

    def __len__(self):
        return len(self.real_cols_to_tsv)

    def is_empty(self):
        return len(self.real_cols_to_tsv) == 0

    def add_column_for_table(self, tsv_col_no_prfx: str, sel_type: str):
        """
            Add a free column during TSV header analysis.
            :param tsv_col_no_prfx: The field name from cvs, e.g. feret for object_feret
            :param sel_type: column type
        """
        assert sel_type in ('n', 't')
        new_max = self.max_by_type[sel_type] + 1
        db_col = "%s%02d" % (sel_type, new_max)
        self.add_association(db_col, tsv_col_no_prfx)

    def as_equal_list(self):
        return encode_equal_list(self.real_cols_to_tsv)
