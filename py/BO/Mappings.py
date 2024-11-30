# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#         Information about mapping process (from TSV to DB)
#
import json
from collections import OrderedDict, namedtuple
from typing import Dict, Tuple, List, Union, Type, Optional, Set, Final, Any

from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import ObjectFields, ObjectHeader
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample

# Typing of parent object tables
ParentTableT = Union[Sample, Acquisition, Process]
ParentTableClassT = Type[ParentTableT]

ANNOTATION_FIELDS: Final = {
    # !!! 2 TSV fields end up into a single DB column, we read both and arbitrate
    "object_annotation_category": {
        "table": ObjectHeader.__tablename__,
        "field": "classif_id",
        "type": "t",
    },
    "object_annotation_category_id": {
        "table": ObjectHeader.__tablename__,
        "field": "classif_id",
        "type": "n",
    },
    "object_annotation_date": {
        "table": ObjectHeader.__tablename__,
        "field": "classif_when",
        "type": "t",
    },
    "object_annotation_person_name": {
        "table": ObjectHeader.__tablename__,
        "field": "classif_who",
        "type": "t",
    },
    "object_annotation_status": {
        "table": ObjectHeader.__tablename__,
        "field": "classif_qual",
        "type": "t",
    },
}
DOUBLED_FIELDS: Final = {
    # Added to object_annotation_date
    "object_annotation_time": {
        "table": ObjectHeader.__tablename__,
        "field": "classif_when",
        "type": "t",
    },
    # Either this one or object_annotation_person_name
    "object_annotation_person_email": {
        "table": ObjectHeader.__tablename__,
        "field": "classif_who",
        "type": "t",
    },
}
PREDEFINED_FIELDS: Final = {
    **ANNOTATION_FIELDS,
    # A mapping from TSV columns to objects and fields
    "object_id": {"table": ObjectHeader.__tablename__, "field": "orig_id", "type": "t"},
    "sample_id": {"table": Sample.__tablename__, "field": "orig_id", "type": "t"},
    "acq_id": {"table": Acquisition.__tablename__, "field": "orig_id", "type": "t"},
    "process_id": {"table": Process.__tablename__, "field": "orig_id", "type": "t"},
    "object_lat": {
        "table": ObjectHeader.__tablename__,
        "field": "latitude",
        "type": "n",
    },
    "object_lon": {
        "table": ObjectHeader.__tablename__,
        "field": "longitude",
        "type": "n",
    },
    "object_date": {
        "table": ObjectHeader.__tablename__,
        "field": "objdate",
        "type": "t",
    },
    "object_time": {
        "table": ObjectHeader.__tablename__,
        "field": "objtime",
        "type": "t",
    },
    "object_link": {
        "table": ObjectHeader.__tablename__,
        "field": "object_link",
        "type": "t",
    },
    "object_depth_min": {
        "table": ObjectHeader.__tablename__,
        "field": "depth_min",
        "type": "n",
    },
    "object_depth_max": {
        "table": ObjectHeader.__tablename__,
        "field": "depth_max",
        "type": "n",
    },
    "complement_info": {
        "table": ObjectHeader.__tablename__,
        "field": "complement_info",
        "type": "t",
    },
    "img_rank": {"table": Image.__tablename__, "field": "imgrank", "type": "n"},
    "img_file_name": {
        "table": Image.__tablename__,
        "field": "orig_file_name",
        "type": "t",
    },
    "sample_dataportal_descriptor": {
        "table": Sample.__tablename__,
        "field": "dataportal_descriptor",
        "type": "t",
    },
    "acq_instrument": {
        "table": Acquisition.__tablename__,
        "field": "instrument",
        "type": "t",
    },
}

# C'est un set de table 😁
POSSIBLE_TABLES: Final = set(
    [v["table"] for v in PREDEFINED_FIELDS.values()] + [ObjectFields.__tablename__]
)  # No hard-coded mapping for this one anymore

PARENT_CLASSES: Final[Dict[str, ParentTableClassT]] = OrderedDict(
    [
        (Sample.__tablename__, Sample),
        (Acquisition.__tablename__, Acquisition),
        (Process.__tablename__, Process),
    ]
)

TARGET_CLASSES: Final = {
    **PARENT_CLASSES,
    ObjectHeader.__tablename__: ObjectHeader,
    ObjectFields.__tablename__: ObjectFields,
    Image.__tablename__: Image,
}

# (f)loat->(n)umerical
POSSIBLE_TYPES: Final = {"[f]": "n", "[t]": "t"}
# TSV prefix to 'real' table name, only for extendable tables
PREFIX_TO_TABLE: Final = {
    "object": ObjectFields.__tablename__,
    "acq": Acquisition.__tablename__,
    "process": Process.__tablename__,
    "sample": Sample.__tablename__,
}
TABLE_TO_PREFIX: Final = {v: k for k, v in PREFIX_TO_TABLE.items()}


# noinspection PyPep8Naming
def TSV_table_to_table(table: str) -> str:
    """
    Return the real table name behind the one used in TSV composed column names.
    """
    return PREFIX_TO_TABLE.get(table, table)


# A re-mapping operation, from and to are real DB columns
RemapOp = namedtuple("RemapOp", ["frm", "to"])

# Typings
MappedTableT = Union[
    ObjectFields, Sample, Acquisition, Process
]  # an instance of one of the 4 classes
MappedTableTypeT = Type[MappedTableT]  # one of the 4 classes themselves

# What is mapped, i.e. has free fields
MAPPED_TABLES: List[MappedTableTypeT] = [ObjectFields, Sample, Acquisition, Process]
MAPPED_TABLES_SET = set(MAPPED_TABLES)

FREE_COLS_ARE_ELSEWHERE = True  # Production, there is object_field table
PHY_COL_TO_EXPERIMENT_COL = lambda col: col  # Production: n01 is in object_field.n01

if False:  # !!! NO COMMIT if True !!!
    # Switch free columns to another storage and/or naming method.
    # DO NOT SET for prod', lol
    # LS: My playground, a single table grouping obj_head and obj_field, accessed e.g. using obj3.free_n[xx]
    ObjectHeader.__tablename__ = "obj_head"
    FREE_COLS_ARE_ELSEWHERE = False
    PHY_COL_TO_EXPERIMENT_COL = lambda col: "free_n[" + col[1:] + "]"


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

    __slots__ = [
        "object_mappings",
        "sample_mappings",
        "acquisition_mappings",
        "process_mappings",
        "all",
        "by_table_name",
        "by_table",
        "was_empty",
    ]

    def __init__(self) -> None:
        self.object_mappings: TableMapping = TableMapping(
            ObjectFields, FREE_COLS_ARE_ELSEWHERE
        )
        self.sample_mappings: TableMapping = TableMapping(Sample)
        self.acquisition_mappings: TableMapping = TableMapping(Acquisition)
        self.process_mappings: TableMapping = TableMapping(Process)
        # store for iteration
        self.all: List[TableMapping] = [
            self.object_mappings,
            self.sample_mappings,
            self.acquisition_mappings,
            self.process_mappings,
        ]
        # for 'generic' access to mappings
        self.by_table_name: Dict[str, TableMapping] = {
            a_mapping.table_name: a_mapping for a_mapping in self.all
        }
        self.by_table: Dict[MappedTableTypeT, TableMapping] = {
            a_mapping.table: a_mapping for a_mapping in self.all
        }
        # to track emptiness after load
        self.was_empty = False

    def write_to_project(self, prj: Project) -> None:
        """
        Write the mappings into given Project, new form.
        """
        prj.mappingobj = self.object_mappings.as_json()
        prj.mappingsample = self.sample_mappings.as_json()
        prj.mappingacq = self.acquisition_mappings.as_json()
        prj.mappingprocess = self.process_mappings.as_json()

    def load_from_project(self, prj: Project) -> "ProjectMapping":
        """
        Load self from Project fields serialization.
        """
        self.object_mappings.load_from_equal_list(prj.mappingobj)
        self.sample_mappings.load_from_equal_list(prj.mappingsample)
        self.acquisition_mappings.load_from_equal_list(prj.mappingacq)
        self.process_mappings.load_from_equal_list(prj.mappingprocess)
        self.was_empty = self.is_empty()
        return self

    def as_dict(self) -> Dict[str, Dict[str, str]]:
        """
        Return the mapping as a serializable object for messaging.
        """
        out_dict = {
            mapping.table_name: mapping.real_cols_to_tsv for mapping in self.all
        }
        return out_dict

    def load_from_dict(self, in_dict: Dict) -> "ProjectMapping":
        """
        Use data produced by @as_dict previous for loading self.
        """
        for a_mapping in self.all:
            a_mapping.load_from_dict(in_dict[a_mapping.table_name])
        self.was_empty = self.is_empty()
        return self

    def add_column(
        self, target_table: str, tsv_table: str, tsv_field: str, sel_type
    ) -> Tuple[bool, str]:
        """
        A new custom column was found, add it into the right bucket.
        :return: True if the target column exists in target table, i.e. if addition was possible.
        """
        for_table: TableMapping = self.by_table_name[target_table]
        ok_exists = for_table.add_column_for_table(tsv_field, sel_type)
        real_col = for_table.tsv_cols_to_real[tsv_field]
        return ok_exists, real_col

    def search_field(self, full_tsv_field: str) -> Optional[Dict]:
        """
        Return the storage (i.e. target of mapping) for a custom field in given table.
        e.g. acq_operator -> {'acquisition', 't02', 't'}
        """
        try:
            prfx, tsv_col = full_tsv_field.split("_", 1)
        except ValueError:
            return None  # Not the expected separator
        table_name = PREFIX_TO_TABLE.get(prfx)
        if table_name is None:
            return None  # Not a known prefix
        mping = self.by_table_name[table_name]
        real_col = mping.tsv_cols_to_real.get(tsv_col)
        if real_col is None:
            return None  # Not a known column for this prefix
        return {"table": table_name, "field": real_col, "type": real_col[0]}

    def all_field_names(self) -> Set[str]:
        """
        Return all mapped field names.
        """
        ret = set()
        for a_mapping in self.all:
            tbl = a_mapping.table_name
            prfx = TABLE_TO_PREFIX.get(tbl, tbl)
            ret.update(a_mapping.tsv_cols_prefixed(prfx))
        return ret

    def is_empty(self):
        for a_mapping in self.all:
            if len(a_mapping.tsv_cols_to_real) > 0:
                return False
        return True


class TableMapping(object):
    """
    The mapping for a given DB table, i.e. from TSV columns to DB ones.
    """

    __slots__ = [
        "table",
        "table_name",
        "real_cols_to_tsv",
        "tsv_cols_to_real",
        "free_cols_separated",
    ]

    def __init__(self, table: MappedTableTypeT, free_ones_are_elsewhere: bool = False):
        self.table: MappedTableTypeT = table
        self.table_name = table.__tablename__
        # key = DB column, val = TSV field name WITHOUT table prefix
        self.real_cols_to_tsv: Dict[str, str] = OrderedDict()
        # key = TSV field name WITHOUT table prefix, val = DB column
        self.tsv_cols_to_real: Dict[str, str] = OrderedDict()
        # indicate if the free columns are in another DB table
        self.free_cols_separated = free_ones_are_elsewhere

    def load_from_equal_list(self, str_mapping: Optional[str]) -> "TableMapping":
        """
        Input has form, e.g.:
            n01=lat_end
            n02=lon_end
            n03=area
        Or now json (text) in the reverse form
            {"lat_end":"n01"...}
            ...
        """
        if not str_mapping:
            # None or "" => nothing to do
            return self
        if str_mapping.startswith("{"):
            self.tsv_cols_to_real = json.loads(str_mapping)
            self.real_cols_to_tsv = {
                v: k
                for k, v in sorted(self.tsv_cols_to_real.items(), key=lambda kv: kv[1])
            }  # Paranoid re-sort
            return self
        real_cols_to_tsv = self.real_cols_to_tsv
        tsv_cols_to_real = self.tsv_cols_to_real
        for a_map in str_mapping.splitlines():
            if not a_map:
                # Empty lines are tolerated
                continue
            db_col, tsv_col_no_prfx = a_map.split("=", 1)
            # self.add_association(db_col, tsv_col_no_prfx)
            # Above is too slow for many (all!) projects, below is an equivalent rewrite
            real_cols_to_tsv[db_col] = tsv_col_no_prfx
            tsv_cols_to_real[tsv_col_no_prfx] = db_col
        return self

    def load_from_dict(self, dict_mapping: dict) -> None:
        for db_col, tsv_col_no_prfx in dict_mapping.items():
            self.add_association(db_col, tsv_col_no_prfx)

    def load_from(self, other: "TableMapping"):
        self.load_from_dict(other.real_cols_to_tsv)

    def add_association(self, db_col, tsv_col_no_prfx) -> None:
        self.real_cols_to_tsv[db_col] = tsv_col_no_prfx
        self.tsv_cols_to_real[tsv_col_no_prfx] = db_col

    def __len__(self) -> int:
        return len(self.real_cols_to_tsv)

    def is_empty(self) -> bool:
        return len(self.real_cols_to_tsv) == 0

    def max_by_type(self, sel_type: str) -> int:
        """
        Return the present maximum value for column type, either 't' or 'n'.
        """
        vals = [
            int(a_col[1:])
            for a_col in self.real_cols_to_tsv.keys()
            if a_col[0] == sel_type
        ]
        if len(vals) == 0:
            return 0
        else:
            return max(vals)

    def add_column_for_table(self, tsv_col_no_prfx: str, sel_type: str) -> bool:
        """
        Add a free column during TSV header analysis.
        :param tsv_col_no_prfx: The field name from cvs, e.g. feret for object_feret
        :param sel_type: column type
        :return: True if the target column exists in table.
        """
        assert sel_type in ("n", "t")
        new_max = self.max_by_type(sel_type) + 1
        db_col = "%s%02d" % (sel_type, new_max)
        self.add_association(db_col, tsv_col_no_prfx)
        return db_col in self.table.__dict__

    def as_equal_list(self) -> str:
        return encode_equal_list(self.real_cols_to_tsv, "\n")

    def as_json(self) -> str:
        return json.dumps(self.tsv_cols_to_real)

    def as_select_list(self, alias: str) -> str:
        """
        Return a SQL select list for given alias.
        """
        sels = []
        tsv_table_name = TABLE_TO_PREFIX[self.table_name]
        for db_col, tsv_fld in self.real_cols_to_tsv.items():
            sels.append('%s.%s AS "%s_%s"' % (alias, db_col, tsv_table_name, tsv_fld))
        return ", " + ", ".join(sels) if sels else ""

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

    def augmented_with(
        self, source: "TableMapping"
    ) -> Tuple["TableMapping", List[RemapOp], List[str]]:
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
                    errs.append(
                        "Column '%s.%s' cannot be mapped. No space left in mapping."
                        % (self.table.__tablename__, a_tsv_src_col)
                    )
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
                    assert real_col_in_dest[0] == a_real_src_col[0], (
                        "Destination column '%s' aka '%s' and source column '%s' aka '%s' have different types!"
                        % (
                            a_tsv_src_col,
                            real_col_in_dest,
                            a_tsv_src_col,
                            a_real_src_col,
                        )
                    )
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

    def find_tsv_cols(self, tsv_cols: List[str]) -> Dict[str, str]:
        """
        Return the corresponding real column for each TSV column provided and present.
        """
        ret = OrderedDict()
        for a_tsv_col in tsv_cols:
            real_col = self.tsv_cols_to_real.get(a_tsv_col)
            if real_col is not None:
                ret[a_tsv_col] = real_col
        return ret

    def tsv_cols_prefixed(self, prfx: str) -> List[str]:
        return [prfx + "_" + tsv_col for tsv_col in self.real_cols_to_tsv.values()]

    def phy_lookup(self, criteria_col: str) -> Tuple[bool, str]:
        """Return real DB column for index-based convention, and where to find it
        e.g. for Objects, n01 -> (True, "n01") as there is obj_fields"""
        criteria_col = PHY_COL_TO_EXPERIMENT_COL(criteria_col)
        if self.free_cols_separated:
            return True, criteria_col
        else:
            return False, criteria_col


def encode_equal_list(a_mapping: Dict[str, Any], sep: str) -> str:
    """
        Turn a dict into a string key=value, with sorted keys.
    :param sep: line separator
    :param a_mapping:
    :return:
    """
    eqs = ["%s=%s" % (k, v) for k, v in a_mapping.items()]
    eqs.sort()
    return sep.join(eqs)
