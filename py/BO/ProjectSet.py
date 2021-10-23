# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A set of projects
#

from dataclasses import dataclass
from typing import List, Dict, Optional, Generator, Tuple

import numpy as np  # type: ignore
from numpy import ndarray

from BO.Classification import ClassifIDT, ClassifIDListT
from BO.Mappings import TableMapping
from BO.Object import ObjectBO
from BO.helpers.DataclassAsDict import DataclassAsDict
from DB import Project, ObjectFields
from DB.Project import ProjectIDListT
from DB.helpers import Session, Result
from DB.helpers.ORM import Query, any_
from helpers.DynamicLogs import get_logger


@dataclass(init=False)
class ProjectSetColumnStats(DataclassAsDict):
    """
        Column statistics for a set of projects.
    """
    proj_ids: ProjectIDListT
    total: int
    columns: List[str]
    counts: List[int]
    variances: List[Optional[float]]


logger = get_logger(__name__)


class FeatureConsistentProjectSet(object):
    """
        Several projects with common columns. Of course, fixed DB columns are common to all objects in all projects
        but, on top, object's free columns can be in common for some of them.
    """

    def __init__(self, session: Session, prj_ids: ProjectIDListT, column_names: List[str]):
        self.session = session
        self.prj_ids = prj_ids
        self.column_names = column_names

    def _projects_with_mappings(self) -> Generator[Tuple[Project, List[str]], None, None]:
        """
            Iterator self list of project, returning them + mapped free columns.
        """
        qry: Query = self.session.query(Project)
        qry = qry.filter(Project.projid == any_(self.prj_ids))
        for a_proj in qry.all():
            free_columns_mappings = TableMapping(ObjectFields).load_from_equal_list(a_proj.mappingobj)
            mapped = ObjectBO.resolve_fields(self.column_names, free_columns_mappings)
            assert len(mapped) == len(self.column_names), "Project %d does not contain all columns" % a_proj.projid
            yield a_proj, mapped

    # TODO: dup code with DescribedObjectSet.get_sql
    PRJ_SQL = ("SELECT {0} "
               "  FROM obj_head obh"
               "  JOIN obj_field obf ON obf.objfid = obh.objid"
               "  JOIN acquisitions acq ON acq.acquisid = obh.acquisid"
               "  JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = {1}"
               " WHERE obh.classif_qual = 'V' ")

    OBJ_COLS = ["objid", "classif_id"]

    def _build_flat_union(self):
        """
            Build a UNION with all common columns + object_id and classif_id
        """
        prj_sql = "(" + self.PRJ_SQL + ")"
        sels_for_prjs = []
        # We have to alias the column in order to have a consistent naming of the CTE
        col_aliases = ["c%d" % num for num in range(len(self.column_names))]
        obj_cols = ",".join(["obh." + a_col for a_col in self.OBJ_COLS])
        # Compose a CTE for each project with its mapped columns
        for a_proj, mapped in self._projects_with_mappings():
            mapped_with_aliases = ["%s AS %s" % (col, als) for col, als in zip(mapped, col_aliases)]
            sels_for_prjs.append(prj_sql.format(obj_cols + "," + ",".join(mapped_with_aliases), a_proj.projid))
        # Final SQL
        sql = "SET LOCAL enable_seqscan=FALSE;"
        sql += "WITH flat AS (" + " UNION ALL ".join(sels_for_prjs) + " ) "
        return col_aliases, sql

    def read_columns_stats(self) -> ProjectSetColumnStats:
        """
            Do some basic stats on the given columns, for validated lines in all given projects.
        """
        col_aliases, sql = self._build_flat_union()
        exprs = ",".join(["COUNT(%s), VARIANCE(%s)"
                          % (als, als) for als in col_aliases])
        sql += "SELECT COUNT(1), " + exprs + " FROM flat "
        sql = self.amend_sql(sql)
        res: Result = self.session.execute(sql)
        vals = res.first()
        total = vals[0]  # first in result line is the count
        counts = vals[1::2]  # then count() every second column
        variances = vals[2::2]  # and variance() the other one
        ret = ProjectSetColumnStats([self.prj_ids, total, self.column_names, counts, variances])
        # cls.read_median_values(session, prj_ids, column_names, 5000)
        return ret

    def read_median_values(self) -> Dict[str, Optional[float]]:
        """
            Compute median value of columns, for all given projects.
             Return a dict with key=column name, value=median for column
        """
        col_aliases, sql = self._build_flat_union()
        exprs = ",".join(["PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY %s) AS med%s"
                          % (als, als) for als in col_aliases])
        # Final SQL
        sql += "SELECT " + exprs + " FROM flat "
        sql = self.amend_sql(sql)
        # Format output
        logger.debug("median SQL: %s", sql)
        res: Result = self.session.execute(sql)
        ret = {col_name: a_val for col_name, a_val in zip(self.column_names, res.first())}
        return ret

    def read_all(self) -> Result:
        """
            Read the whole dataset, returning the cursor to avoid expensive memoization.
        """
        col_aliases, sql = self._build_flat_union()
        exprs = ",".join(self.OBJ_COLS + col_aliases)
        # Final SQL
        sql += "SELECT " + exprs + " FROM flat "
        sql = self.amend_sql(sql)
        # Format output
        logger.debug("read_all SQL: %s", sql)
        res: Result = self.session.execute(sql)
        return res

    def np_read_all(self) -> Tuple[ndarray, List[int], ClassifIDListT]:  # TODO: ObjectIDListT
        """
            Read the dataset as a numpy array. NULL and infinities become an np NaN.
        """
        res = self.read_all()
        obj_ids: List[int] = []
        classif_ids: ClassifIDListT = []
        # noinspection PyUnresolvedReferences
        np_table = self.np_read(res, res.rowcount, self.column_names,
                                obj_ids, classif_ids, {})
        return np_table, obj_ids, classif_ids

    @staticmethod
    def np_read(res, nb_lines, columns, obj_ids, classif_ids, replacements):
        # Allocate memory in one go
        # TODO: float32 is a shameless attempt to save memory
        np_table = np.ndarray(shape=(nb_lines, len(columns)), dtype=np.float32)
        nan = float("nan")
        not_known = {float("inf"), float("-inf"), nan, None}
        repl_get = replacements.get
        for ndx in range(nb_lines):
            try:
                objid, classif_id, *vals = next(res)
            except StopIteration:
                # crop the resulting NP
                np_table.resize((ndx, len(columns)), refcheck=False)
                break
            vals = [repl_get(a_col, nan) if a_val in not_known else a_val
                    for a_val, a_col in zip(vals, columns)]  # Map all absent values
            obj_ids.append(objid)
            classif_ids.append(classif_id)
            np_table[ndx] = vals
        return np_table

    def np_stats(self, nb_table: ndarray) -> Tuple[Dict, Dict]:
        # Compute medians & variance per _present_ feature
        np_medians_per_col = {}
        np_variances_per_col = {}
        for ndx, a_col in enumerate(self.column_names):
            feat_col = nb_table[:, ndx]
            # Clean from NaNs
            clean_col_col = feat_col[~np.isnan(feat_col)]
            np_median = np.median(clean_col_col)
            np_variance = np.var(clean_col_col)
            np_medians_per_col[a_col] = np_median
            np_variances_per_col[a_col] = np_variance
        return np_medians_per_col, np_variances_per_col

    def amend_sql(self, sql):
        return sql


class LimitedInCategoriesProjectSet(FeatureConsistentProjectSet):
    """
       Same as parent class, except that inside the projects we sample objects pseudo-randomly per category,
       for given categories. Or filter using given categories.
    """

    def __init__(self, session: Session, prj_ids: ProjectIDListT, column_names: List[str],
                 random_limit: Optional[int], categories: List[ClassifIDT]):
        """
             :param random_limit: If set, pick only 'fixed random' objects number from each category, inside
             each project from the dataset.
             :param categories: If valued, pick only objects with given classification.
             Otherwise, the subclass just does the same as its base.
        """
        assert random_limit is None or (random_limit is not None and len(categories) > 0)
        super().__init__(session=session, prj_ids=prj_ids, column_names=column_names)
        self.random_limit = random_limit
        self.categories = categories

    def _add_random_limit(self, sql):
        prj_in_list = ",".join([str(prj_id) for prj_id in self.prj_ids])
        categ_in_list = ",".join([str(classif_id) for classif_id in self.categories])
        sql += (" WHERE flat.objid IN "
                " ( SELECT q.objid FROM "
                " ( SELECT obh2.objid, ROW_NUMBER() OVER (PARTITION BY obh2.classif_id "
                "                                         ORDER BY obh2.random_value) rank "
                "     FROM obj_head obh2"
                "     JOIN acquisitions acq2 ON acq2.acquisid = obh2.acquisid"
                "     JOIN samples sam2 ON sam2.sampleid = acq2.acq_sample_id AND sam2.projid IN ({0})"
                "    WHERE obh2.classif_qual = 'V' AND obh2.classif_id IN ({2})) q"
                "   WHERE rank <= {1} )").format(prj_in_list, self.random_limit, categ_in_list)
        return sql

    def _add_category_filter(self, sql):
        categ_in_list = ",".join([str(classif_id) for classif_id in self.categories])
        sql += " WHERE flat.classif_id IN ({0}) ".format(categ_in_list)
        return sql

    def amend_sql(self, sql: str):
        if self.random_limit is not None:
            return self._add_random_limit(sql)
        elif len(self.categories) > 0:
            return self._add_category_filter(sql)
        return sql
