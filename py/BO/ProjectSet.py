# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A set of projects
#

from dataclasses import dataclass
from typing import List, Dict, Optional, Generator, Tuple

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
        Several projects with common columns. Of course, fixed DB columns are common to all projects,
        but, on top, object's free columns can be in common for some of them.
    """

    def __init__(self):
        pass

    @classmethod
    def _projects_with_mappings(cls, session: Session, prj_ids: ProjectIDListT, column_names: List[str]) \
            -> Generator[Tuple[Project, List[str]], None, None]:
        """ Iterator over a list of project, returning them + mapped free columns """
        qry: Query = session.query(Project)
        qry = qry.filter(Project.projid == any_(prj_ids))
        for a_proj in qry.all():
            free_columns_mappings = TableMapping(ObjectFields).load_from_equal_list(a_proj.mappingobj)
            mapped = ObjectBO.resolve_fields(column_names, free_columns_mappings)
            assert len(mapped) == len(column_names), "Project %d does not contain all columns" % a_proj.projid
            yield a_proj, mapped

    PRJ_SQL = ("SELECT {0} "
               "  FROM obj_head obh"
               "  JOIN obj_field obf ON obf.objfid = obh.objid"
               "  JOIN acquisitions acq ON acq.acquisid = obh.acquisid"
               "  JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = {1}"
               " WHERE obh.classif_qual = 'V' ")

    @classmethod
    def read_columns_stats(cls, session: Session, prj_ids: ProjectIDListT, column_names: List[str]) \
            -> ProjectSetColumnStats:
        """
            Do some basic stats on the given columns, for validated lines in all given projects.
        """
        prj_sql = "(" + cls.PRJ_SQL + " LIMIT 50000)"
        sels_for_prjs = []
        # We have to alias the column in order to have a consistent naming of the CTE
        col_aliases = ["c%d" % num for num in range(len(column_names))]
        # Compose a CTE for each project with its mapped columns
        for a_proj, mapped in cls._projects_with_mappings(session, prj_ids, column_names):
            mapped_with_aliases = ["%s AS %s" % (col, als) for col, als in zip(mapped, col_aliases)]
            sels_for_prjs.append(prj_sql.format(",".join(mapped_with_aliases), a_proj.projid))
        # Final SQL
        sql = "SET LOCAL enable_seqscan=FALSE;"
        sql += "WITH flat AS (" + " UNION ALL ".join(sels_for_prjs) + " ) "
        exprs = ",".join(["COUNT(%s), VARIANCE(%s)" % (als, als) for als in col_aliases])
        sql += "SELECT COUNT(1), " + exprs + " FROM flat "
        res: Result = session.execute(sql)
        vals = res.first()
        total = vals[0]  # first in result line is the count
        counts = vals[1::2]  # then count() every second column
        variances = vals[2::2]  # and variance() the other one
        ret = ProjectSetColumnStats([prj_ids, total, column_names, counts, variances])
        # cls.read_median_values(session, prj_ids, column_names, 5000)
        return ret

    ACQ_CTE = (" acq{0} AS (SELECT acq.* "
               "  FROM acquisitions acq"
               "  JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = {0})")

    PRJ_SQL_USING_CTE = ("SELECT {0} "
                         "  FROM obj_head obh"
                         "  JOIN obj_field obf ON obf.objfid = obh.objid"
                         "  JOIN acq{1} ON acq{1}.acquisid = obh.acquisid"
                         " WHERE obh.classif_qual = 'V' ")

    # noinspection PyIncorrectDocstring
    @classmethod
    def read_median_values(cls, session: Session, prj_ids: ProjectIDListT, column_names: List[str],
                           random_limit: Optional[int] = None) \
            -> Dict[int, Dict[str, Optional[float]]]:
        """
            Compute median value of columns, for all given projects.
            :param random_limit: If set, pick only 'fixed random' objects number from each category, inside
             each project from the dataset.
             Return a dict key=project id, value = dict with key=column name, value=median for column
        """
        # We have to alias the column in order to have a consistent naming of the UNION
        col_aliases = ["c%d" % num for num in range(len(column_names))]
        # Compose a query for each project with its mapped columns
        acq_ctes = []
        sel_by_prj = []
        for a_proj, mapped in cls._projects_with_mappings(session, prj_ids, column_names):
            acq_ctes.append(cls.ACQ_CTE.format(a_proj.projid))
            expr_with_alias = ["PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY %s) AS %s"
                               % (col, als) for col, als in zip(mapped, col_aliases)]
            sel_for_prj = " %s AS projid, " % a_proj.projid + ",".join(expr_with_alias)
            sel_by_prj.append(cls.PRJ_SQL_USING_CTE.format(sel_for_prj, a_proj.projid))
            if random_limit is not None:
                sel_by_prj[-1] += (" AND obh.objid IN "
                                   " ( SELECT q.objid FROM "
                                   " ( SELECT obh2.objid, ROW_NUMBER() OVER (PARTITION BY obh2.classif_id "
                                   "                                         ORDER BY obh2.random_value) rank "
                                   "     FROM obj_head obh2"
                                   "     JOIN acq{0} ON acq{0}.acquisid = obh2.acquisid"
                                   "    WHERE obh2.classif_qual = 'V' ) q"
                                   "   WHERE rank <= {1} )").format(a_proj.projid, random_limit)
        # Final SQL
        sql = "SET LOCAL enable_seqscan=FALSE;"
        sql += "WITH " + ",".join(acq_ctes)
        sql += " UNION ALL ".join(sel_by_prj)
        # Format output
        logger.info("median SQL: %s", sql)
        res: Result = session.execute(sql)
        ret = {}
        for a_res in res:
            projid, *vals = a_res
            ret[projid] = {col_name: a_val for col_name, a_val in zip(column_names, vals)}
        return ret
