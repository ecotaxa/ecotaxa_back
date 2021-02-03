# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from collections import OrderedDict, namedtuple
from typing import Dict, Tuple, List, Union, Type, Optional

from BO.helpers.TSVHelpers import encode_equal_list
from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import ObjectFields, ObjectHeader
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample

# Typing of parent object tables
ParentTableT = Union[Sample, Acquisition, Process]
ParentTableClassT = Type[ParentTableT]


class GlobalMapping(object):
    """
        Information about mapping process (from TSV to DB)
    """
    ANNOTATION_FIELDS = {
        # !!! 2 TSV fields end up into a single DB column
        'object_annotation_category': {'table': ObjectHeader.__tablename__, 'field': 'classif_id', 'type': 't'},
        'object_annotation_category_id': {'table': ObjectHeader.__tablename__, 'field': 'classif_id', 'type': 'n'},
        'object_annotation_date': {'table': ObjectHeader.__tablename__, 'field': 'classif_when', 'type': 't'},
        'object_annotation_person_name': {'table': ObjectHeader.__tablename__, 'field': 'classif_who', 'type': 't'},
        'object_annotation_status': {'table': ObjectHeader.__tablename__, 'field': 'classif_qual', 'type': 't'},
    }
    PREDEFINED_FIELDS = {
        **ANNOTATION_FIELDS,
        # A mapping from TSV columns to objects and fields
        'object_id': {'table': ObjectHeader.__tablename__, 'field': 'orig_id', 'type': 't'},
        'sample_id': {'table': Sample.__tablename__, 'field': 'orig_id', 'type': 't'},
        'acq_id': {'table': Acquisition.__tablename__, 'field': 'orig_id', 'type': 't'},
        'process_id': {'table': Process.__tablename__, 'field': 'orig_id', 'type': 't'},
        'object_lat': {'table': ObjectHeader.__tablename__, 'field': 'latitude', 'type': 'n'},
        'object_lon': {'table': ObjectHeader.__tablename__, 'field': 'longitude', 'type': 'n'},
        'object_date': {'table': ObjectHeader.__tablename__, 'field': 'objdate', 'type': 't'},
        'object_time': {'table': ObjectHeader.__tablename__, 'field': 'objtime', 'type': 't'},
        'object_link': {'table': ObjectHeader.__tablename__, 'field': 'object_link', 'type': 't'},
        'object_depth_min': {'table': ObjectHeader.__tablename__, 'field': 'depth_min', 'type': 'n'},
        'object_depth_max': {'table': ObjectHeader.__tablename__, 'field': 'depth_max', 'type': 'n'},
        'img_rank': {'table': Image.__tablename__, 'field': 'imgrank', 'type': 'n'},
        'img_file_name': {'table': Image.__tablename__, 'field': 'orig_file_name', 'type': 't'},
        'sample_dataportal_descriptor': {'table': Sample.__tablename__, 'field': 'dataportal_descriptor', 'type': 't'},
        'acq_instrument': {'table': Acquisition.__tablename__, 'field': 'instrument', 'type': 't'},
    }

    # C'est un set de table 😁
    POSSIBLE_TABLES = set([v['table'] for v in PREDEFINED_FIELDS.values()] +
                          [ObjectFields.__tablename__])  # No hard-coded mapping for this one anymore

    PARENT_CLASSES: Dict[str, ParentTableClassT] = OrderedDict([(Sample.__tablename__, Sample),
                                                                (Acquisition.__tablename__, Acquisition),
                                                                (Process.__tablename__, Process)])

    TARGET_CLASSES = {**PARENT_CLASSES,
                      ObjectHeader.__tablename__: ObjectHeader,
                      ObjectFields.__tablename__: ObjectFields,
                      Image.__tablename__: Image}

    # (f)loat->(n)umerical
    POSSIBLE_TYPES = {'[f]': 'n', '[t]': 't'}
    # TSV prefix to 'real' table name, only for extendable tables
    PREFIX_TO_TABLE = {
        'object': ObjectFields.__tablename__,
        'acq': Acquisition.__tablename__,
        'process': Process.__tablename__,
        'sample': Sample.__tablename__,
    }
    TABLE_TO_PREFIX = {v: k for k, v in PREFIX_TO_TABLE.items()}

    # noinspection PyPep8Naming
    @classmethod
    def TSV_table_to_table(cls, table):
        """
            Return the real table name behind the one used in TSV composed column names.
        """
        return cls.PREFIX_TO_TABLE.get(table, table)


# A re-mapping operation, from and to are real DB columns
RemapOp = namedtuple("RemapOp", ['frm', 'to'])

# Typings
MappedTableT = Union[ObjectFields, Sample, Acquisition, Process]  # an instance of one of the 4 classes
MappedTableTypeT = Type[MappedTableT]  # one of the 4 classes themselves

# What is mapped, i.e. has free fields
MAPPED_TABLES: List[MappedTableTypeT] = [ObjectFields, Sample, Acquisition, Process]
MAPPED_TABLES_SET = set(MAPPED_TABLES)


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
        self.object_mappings: TableMapping = TableMapping(ObjectFields)
        self.sample_mappings: TableMapping = TableMapping(Sample)
        self.acquisition_mappings: TableMapping = TableMapping(Acquisition)
        self.process_mappings: TableMapping = TableMapping(Process)
        # store for iteration
        self.all: List[TableMapping] = [self.object_mappings, self.sample_mappings,
                                        self.acquisition_mappings, self.process_mappings]
        # for 'generic' access to mappings
        self.by_table_name: Dict[str, TableMapping] = {a_mapping.table_name: a_mapping for a_mapping in self.all}
        self.by_table: Dict[MappedTableTypeT, TableMapping] = {a_mapping.table: a_mapping for a_mapping in self.all}
        # for fast lookup from TSV analysis
        # key = TSV full column, val = ( TableMapping, DB col )
        self.all_fields: Dict[str, Tuple[TableMapping, str]] = dict()
        # to track emptiness after load
        self.was_empty = False

    def write_to_project(self, prj: Project) -> None:
        """
            Write the mappings into given Project .
        """
        prj.mappingobj = self.object_mappings.as_equal_list()
        prj.mappingsample = self.sample_mappings.as_equal_list()
        prj.mappingacq = self.acquisition_mappings.as_equal_list()
        prj.mappingprocess = self.process_mappings.as_equal_list()

    def load_from_project(self, prj: Project) -> 'ProjectMapping':
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
        out_dict = {mapping.table_name: mapping.real_cols_to_tsv
                    for mapping in self.all}
        return out_dict

    def load_from_dict(self, in_dict: Dict):
        """
            Use data produced by @as_dict previous for loading self.
        """
        for a_mapping in self.all:
            a_mapping.load_from_dict(in_dict[a_mapping.table_name])
        self.build_all_fields()
        return self

    def add_column(self, target_table: str, tsv_table: str, tsv_field: str, sel_type) -> Tuple[bool, str]:
        """
            A new custom column was found, add it into the right bucket.
            :return: True if the target column exists in target table, i.e. if addition was possible.
        """
        for_table: TableMapping = self.by_table_name[target_table]
        ok_exists = for_table.add_column_for_table(tsv_field, sel_type)
        real_col = for_table.tsv_cols_to_real[tsv_field]
        self.all_fields["%s_%s" % (tsv_table, tsv_field)] = (for_table, real_col)
        return ok_exists, real_col

    def search_field(self, full_tsv_field: str) -> Optional[Dict]:
        """
            Return the storage (i.e. target of mapping) for a custom field in given table.
        """
        lookup = self.all_fields.get(full_tsv_field)
        if lookup is None:
            return None
        (mping, real_col) = lookup
        return {'table': mping.table_name, 'field': real_col, 'type': real_col[0]}

    def build_all_fields(self):
        """
            Build cache all_fields for lookup.
        """
        all_fields = {}
        for a_mapping in self.all:
            tbl = a_mapping.table_name
            prfx = GlobalMapping.TABLE_TO_PREFIX.get(tbl, tbl)
            for real_col, tsv_col in a_mapping.real_cols_to_tsv.items():
                all_fields["%s_%s" % (prfx, tsv_col)] = (a_mapping, real_col)
        self.all_fields = all_fields
        self.was_empty = len(all_fields) == 0


class TableMapping(object):
    """
        The mapping for a given DB table, i.e. from TSV columns to DB ones.
    """

    def __init__(self, table: MappedTableTypeT):
        self.table: MappedTableTypeT = table
        self.table_name = table.__tablename__
        # key = DB column, val = TSV field name WITHOUT table prefix
        self.real_cols_to_tsv: Dict[str, str] = OrderedDict()
        # key = TSV field name WITHOUT table prefix, val = DB column
        self.tsv_cols_to_real: Dict[str, str] = OrderedDict()
        self.max_by_type = {'n': 0, 't': 0}

    def load_from_equal_list(self, str_mapping: Optional[str]):
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
        real_cols_to_tsv = self.real_cols_to_tsv
        tsv_cols_to_real = self.tsv_cols_to_real
        vals_by_type: Dict[str, List[int]] = {}
        for a_map in str_mapping.splitlines():
            if not a_map:
                # Empty lines are tolerated
                continue
            db_col, tsv_col_no_prfx = a_map.split('=', 1)
            self.add_association(db_col, tsv_col_no_prfx)
            # Above is too slow for many (all!) projects, below is an equivalent rewrite
            real_cols_to_tsv[db_col] = tsv_col_no_prfx
            tsv_cols_to_real[tsv_col_no_prfx] = db_col
            db_col_type = db_col[0]  # i.e. 't' or 'n'
            db_col_ndx = int(db_col[1:])
            # Store values instead of recomputing maximum for each addition
            vals_by_type.setdefault(db_col_type, []).append(db_col_ndx)
        for a_col_type, vals_for_type in vals_by_type.items():
            self.max_by_type[a_col_type] = max(vals_for_type)
        return self

    def load_from_dict(self, dict_mapping: dict):
        for db_col, tsv_col_no_prfx in dict_mapping.items():
            self.add_association(db_col, tsv_col_no_prfx)

    def load_from(self, other: 'TableMapping'):
        self.load_from_dict(other.real_cols_to_tsv)

    def add_association(self, db_col, tsv_col_no_prfx):
        self.real_cols_to_tsv[db_col] = tsv_col_no_prfx
        self.tsv_cols_to_real[tsv_col_no_prfx] = db_col
        self.adjust_max(db_col, self.max_by_type)

    @staticmethod
    def adjust_max(db_col, max_by_type):
        # Adjust maximum for type
        db_col_type = db_col[0]  # i.e. 't' or 'n'
        db_col_ndx = int(db_col[1:])
        if db_col_ndx > max_by_type[db_col_type]:
            max_by_type[db_col_type] = db_col_ndx

    def __len__(self):
        return len(self.real_cols_to_tsv)

    def is_empty(self):
        return len(self.real_cols_to_tsv) == 0

    def add_column_for_table(self, tsv_col_no_prfx: str, sel_type: str) -> bool:
        """
            Add a free column during TSV header analysis.
            :param tsv_col_no_prfx: The field name from cvs, e.g. feret for object_feret
            :param sel_type: column type
            :return: True if the target column exists in table.
        """
        assert sel_type in ('n', 't')
        new_max = self.max_by_type[sel_type] + 1
        db_col = "%s%02d" % (sel_type, new_max)
        self.add_association(db_col, tsv_col_no_prfx)
        return db_col in self.table.__dict__

    def as_equal_list(self):
        return encode_equal_list(self.real_cols_to_tsv, "\n")

    def transforms_from(self, other):
        """
            Return what should be applied to other in order to stick to self.
        """
        ret = []
        for a_real, a_tsv in other.real_cols_to_tsv.items():
            self_real = self.tsv_cols_to_real[a_tsv]
            if self_real != a_real:
                # output the transform
                ret.append((a_real, self_real))
        return ret

    def augmented_with(self, source: 'TableMapping') -> \
            Tuple['TableMapping', List[RemapOp], List[str]]:
        """
            Compute a new mapping self + source. Returns it, plus the necessary operations to do on source
            so that it fits in result, plus eventual problems preventing to do so.
        """
        assert self.table == source.table
        ret = TableMapping(self.table)
        remaps = []
        errs = []
        # Result must contain at least all columns from self
        ret.load_from(self)
        for a_real_src_col, a_tsv_src_col in source.real_cols_to_tsv.items():
            real_col_in_dest = ret.tsv_cols_to_real.get(a_tsv_src_col)
            if real_col_in_dest is None:
                # TSV column is not present we need a new one
                add_ok = ret.add_column_for_table(a_tsv_src_col, a_real_src_col[0])
                if not add_ok:
                    errs.append("Column '%s.%s' cannot be mapped. No space left in mapping."
                                % (self.table.__tablename__, a_tsv_src_col))
                else:
                    # The new column will get values from old column
                    real_col_in_dest = ret.tsv_cols_to_real.get(a_tsv_src_col)
                    if real_col_in_dest != a_real_src_col:
                        # Remap if different
                        remaps.append(RemapOp(a_real_src_col, real_col_in_dest))
            else:
                if real_col_in_dest != a_real_src_col:
                    # TSV column is present but mapped to a different DB column...
                    # hopefully of same type
                    assert real_col_in_dest[0] == a_real_src_col[0]
                    remaps.append(RemapOp(a_real_src_col, real_col_in_dest))
                else:
                    # TSV column is present and mapped to the same column
                    pass
        # Source columns which were not targets as well get a NULL
        dst_cols = set([a_remap.to for a_remap in remaps])
        src_cols = set([a_remap.frm for a_remap in remaps])
        for a_col in sorted(src_cols.difference(dst_cols)):
            remaps.append(RemapOp(None, a_col))
        return ret, remaps, errs

    def find_tsv_cols(self, tsv_cols: List[str]) -> List[str]:
        """
            Return the corresponding real column for each TSV column provided.
            len(tsv_cols) !=  len(returned value) is an error condition.
        """
        ret = []
        for a_tsv_col in tsv_cols:
            real_col = self.tsv_cols_to_real.get(a_tsv_col)
            if real_col is not None:
                ret.append(real_col)
        return ret
