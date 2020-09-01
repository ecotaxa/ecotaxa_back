# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import datetime
from typing import List, Dict, Any, Iterable

from sqlalchemy.orm import Query

from BO.Mappings import RemapOp, MappedTableTypeT
from DB import ObjectHeader, Sample, ProjectPrivilege, User, Project, ObjectFields
from DB import Session, ResultProxy
from DB.ProjectPrivilege import MANAGE
from DB.User import Role
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


class ProjectBO(object):
    """
        A Project business object. So far just a container for static API_operations involving it.
    """

    @staticmethod
    def update_stats(session: Session, projid: int):
        session.execute("""
        UPDATE projects
           SET objcount=q.nbr, pctclassified=100.0*nbrclassified/q.nbr, pctvalidated=100.0*nbrvalidated/q.nbr
          FROM projects p
          LEFT JOIN
             (SELECT projid, SUM(nbr) nbr, SUM(case when id>0 THEN nbr end) nbrclassified, SUM(nbr_v) nbrvalidated
                FROM projects_taxo_stat
               WHERE projid = :prjid
              GROUP BY projid) q ON p.projid = q.projid
        WHERE projects.projid = :prjid 
          AND p.projid = :prjid""",
                        {'prjid': projid})

    @staticmethod
    def update_taxo_stats(session: Session, projid: int):
        # TODO: There is a direct ref. to obj_head.projid. Problem in case of clean hierarchy.
        session.execute("""
        BEGIN;
        DELETE FROM projects_taxo_stat 
         WHERE projid = :prjid;
        INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p) 
        SELECT projid, COALESCE(classif_id, -1) id, COUNT(*) nbr, 
               COUNT(case WHEN classif_qual = 'V' THEN 1 END) nbr_v,
               COUNT(case WHEN classif_qual = 'D' THEN 1 END) nbr_d, 
               COUNT(case WHEN classif_qual = 'P' THEN 1 END) nbr_p
          FROM obj_head
         WHERE projid = :prjid
        GROUP BY projid, classif_id;
        COMMIT;""",
                        {'prjid': projid})

    @staticmethod
    def projects_for_user(session: Session, user: User,
                          for_managing: bool = False,
                          also_others: bool = False,
                          title_filter: str = '',
                          instrument_filter: str = '',
                          filter_subset: bool = False) -> List:
        """
        :param session:
        :param user: The user for which the list is needed.
        :param for_managing: If set, list the projects that the user can manage.
        :param also_others: If set, also list the projects on which given user has no right, so user can
                                request access to them.
        :param title_filter: If set, filter out the projects with title not matching the required string,
                                or if set to a number, filter out the projects of which ID does not match.
        :param instrument_filter: If set, filter out the projects which do not have given instrument in at least
                                     one sample.
        :param filter_subset: If set, filter out project of which title contains 'subset'.
        :return:
        """
        sql_params: Dict[str, Any] = {"user_id": user.id}

        # Default query: all projects, eventually with first manager information
        sql = """SELECT p.projid, p.title, p.status, 
                        COALESCE(p.objcount,0) as objcount, COALESCE(p.pctvalidated,0) as pctvalidated,
                        COALESCE(p.pctclassified,0) as pctclassified, fpm.email, fpm.name, p.visible
                   FROM projects p
                   LEFT JOIN ( """ + ProjectPrivilege.first_manager_by_project() + """ ) fpm 
                     ON fpm.projid = p.projid """
        if also_others:
            # Add the projects for which no entry is found in ProjectPrivilege
            sql += """
                   LEFT JOIN projectspriv pp ON p.projid = pp.projid AND pp.member = :user_id
                  WHERE pp.member is null """
        else:
            if not user.has_role(Role.APP_ADMINISTRATOR):
                # Not an admin, so restrict to projects which current user can work on
                sql += """
                        JOIN projectspriv pp 
                          ON p.projid = pp.projid 
                         AND pp.member = :user_id """
                if for_managing:
                    sql += """
                         AND pp.privilege = '%s' """ % MANAGE
            sql += " WHERE 1 = 1 "

        if title_filter != '':
            sql += """ 
                    AND ( title ilike '%%'|| :title ||'%%'
                          OR TO_CHAR(p.projid,'999999') LIKE '%%'|| :title ) """
            sql_params["title"] = title_filter

        if instrument_filter != '':
            sql += """
                     AND p.projid IN (SELECT DISTINCT projid FROM acquisitions 
                                       WHERE instrument ILIKE '%%'|| :instrum ||'%%' ) """
            sql_params["instrum"] = instrument_filter

        if filter_subset:
            sql += """
                     AND NOT title ILIKE '%%subset%%'  """

        sql += " ORDER BY LOWER(p.title)"  # pp.member nulls last,

        with CodeTimer("Projects query:", logger):
            res: ResultProxy = session.execute(sql, sql_params)
            ret = res.fetchall()
        return ret

    @classmethod
    def get_bounding_geo(cls, session: Session, proj_id: int) -> Iterable[float]:
        res: ResultProxy = session.execute(
            "SELECT min(o.latitude), max(o.latitude), min(o.longitude), max(o.longitude)"
            "  FROM objects o "
            " WHERE o.projid = :prj",
            {"prj": proj_id})
        vals = res.first()
        assert vals
        return [a_val for a_val in vals]

    @classmethod
    def get_date_range(cls, session: Session, proj_id: int) -> Iterable[datetime]:
        res: ResultProxy = session.execute(
            "SELECT min(o.objdate), max(o.objdate)"
            "  FROM objects o "
            " WHERE o.projid = :prj",
            {"prj": proj_id})
        vals = res.first()
        assert vals
        return [a_val for a_val in vals]

    @staticmethod
    def do_after_load(session: Session, prj_id: int):
        """
            After loading of data, update various cross counts.
        """
        # Ensure the ORM has no shadow copy before going to plain SQL
        session.expunge_all()
        ObjectHeader.update_counts_and_img0(session, prj_id)
        Sample.propagate_geo(session, prj_id)
        ProjectBO.update_taxo_stats(session, prj_id)
        # Stats depend on taxo stats
        ProjectBO.update_stats(session, prj_id)

    @staticmethod
    def delete(session: Session, prj_id: int):
        """
            Completely remove the project.
        """
        # TODO: Remove for user prefs
        # Remove project
        session.query(Project).filter(Project.projid == prj_id).delete()
        # Remove privileges
        session.query(ProjectPrivilege).filter(ProjectPrivilege.projid == prj_id).delete()

    @staticmethod
    def remap(session: Session, prj_id: int, table: MappedTableTypeT, remaps: List[RemapOp]):
        """
            Apply remapping operations onto the given table for given project.
        """
        assert table != ObjectFields
        # Do the remapping, including blanking of unused columns
        values = {a_remap.to: a_remap.frm for a_remap in remaps}
        qry: Query = session.query(table)
        if table == ObjectFields:
            # All tables have direct projid column except ObjectFields
            qry = qry.join(ObjectHeader).filter(ObjectHeader.projid == prj_id)
        else:
            qry = qry.filter(table.projid == prj_id)  # type: ignore
        qry = qry.update(values=values, synchronize_session=False)

        logger.info("Remap query for %s: %s", table.__tablename__, qry)
