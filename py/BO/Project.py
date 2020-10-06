# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import datetime
from typing import List, Dict, Any, Iterable, Optional

from BO.Classification import ClassifIDListT
from BO.Mappings import RemapOp, MappedTableTypeT, ProjectMapping
from BO.ProjectPrivilege import ProjectPrivilegeBO
from DB import ObjectHeader, Sample, ProjectPrivilege, User, Project, ObjectFields, Acquisition, Process, \
    ParticleProject, ParticleCategoryHistogramList, ParticleSample, ParticleCategoryHistogram
from DB import Session, ResultProxy
from DB.User import Role
from DB.helpers.ORM import Delete, Query
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)

# Typings, to be clear that these are not e.g. object IDs
ProjectIDListT = List[int]


class ProjectBO(object):
    """
        A Project business object. So far mainly a container for static API_operations involving it.
    """

    def __init__(self, session: Session, prj_id: int):
        self.project: Optional[Project] = session.query(Project).get(prj_id)

    def get_preset(self) -> ClassifIDListT:
        """
            Return the list of preset classification IDs.
        """
        if not self.project:
            return []
        init_list = self.project.initclassiflist
        if not init_list:
            return []
        return [int(cl_id) for cl_id in init_list.split(",")]

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
        :param filter_subset: If set, filter out any project of which title contains 'subset'.
        :return:
        """
        sql_params: Dict[str, Any] = {"user_id": user.id}

        # Default query: all projects, eventually with first manager information
        sql = """SELECT p.projid, p.title, p.status, 
                        COALESCE(p.objcount,0) AS objcount, COALESCE(p.pctvalidated,0) AS pctvalidated,
                        COALESCE(p.pctclassified,0) AS pctclassified, fpm.email, fpm.name, p.visible
                   FROM projects p
                   LEFT JOIN ( """ + ProjectPrivilegeBO.first_manager_by_project() + """ ) fpm 
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
                         AND pp.privilege = '%s' """ % ProjectPrivilegeBO.MANAGE
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
    def delete_object_parents(session: Session, prj_id: int) -> List[int]:
        """
            Remove object parents, also project children entities, in the project.
        """
        # The EcoTaxa samples which are going to disappear. We have to cleanup Particle side.
        soon_deleted_samples = Query(Sample.sampleid).filter(Sample.projid == prj_id)
        # The EcoPart samples to clean.
        soon_invalid_part_samples = Query(ParticleSample.psampleid).filter(
            ParticleSample.sampleid.in_(soon_deleted_samples))

        # Cleanup EcoPart corresponding tables
        del_qry = ParticleCategoryHistogramList.__table__. \
            delete().where(ParticleCategoryHistogramList.psampleid.in_(soon_invalid_part_samples))
        logger.info("Del part histo lst :%s", str(del_qry))
        session.execute(del_qry)
        del_qry = ParticleCategoryHistogram.__table__. \
            delete().where(ParticleCategoryHistogram.psampleid.in_(soon_invalid_part_samples))
        logger.info("Del part histo :%s", str(del_qry))
        session.execute(del_qry)
        upd_qry = ParticleSample.__table__. \
            update().where(ParticleSample.psampleid.in_(soon_invalid_part_samples)).values(sampleid=None)
        logger.info("Upd part samples :%s", str(upd_qry))
        row_count = session.execute(upd_qry).rowcount
        logger.info(" %d EcoPart samples unlinked and cleaned", row_count)

        ret = []
        # Remove first-level children of project
        for a_tbl in (Sample, Acquisition, Process):
            sub_del: Delete = a_tbl.__table__.delete().where(a_tbl.projid == prj_id)  # type: ignore
            logger.info("Del parent :%s", str(sub_del))
            row_count = session.execute(sub_del).rowcount
            ret.append(row_count)
            logger.info("%d rows deleted", row_count)
            if row_count > 1000:
                session.commit()
        session.commit()
        return ret

    @staticmethod
    def delete(session: Session, prj_id: int):
        """
            Completely remove the project. It is assumed that contained objects has been removed.
        """
        # TODO: Remove for user prefs
        # Unlink Particle project if any
        upd_qry = ParticleProject.__table__.update().where(ParticleProject.projid == prj_id).values(projid=None)
        row_count = session.execute(upd_qry).rowcount
        if row_count:
            logger.info("%d EcoPart project unlinked", row_count)
        # Remove project
        session.query(Project). \
            filter(Project.projid == prj_id).delete()
        # Remove privileges
        session.query(ProjectPrivilege). \
            filter(ProjectPrivilege.projid == prj_id).delete()

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

    @classmethod
    def get_all_object_ids(cls, session: Session, prj_id: int):  # TODO: Problem with recursive import -> ObjetIdListT:
        """
            Return the full list of objects IDs inside a project.
            TODO: Maybe better in ObjectBO
        """
        qry: Query = session.query(ObjectHeader.objid).filter(ObjectHeader.projid == prj_id)
        return [an_id for an_id in qry.all()]

    @classmethod
    def enrich(cls, prj: Project):
        """
            Add mappings in serializable form.
        """
        mappings = ProjectMapping()
        mappings.load_from_project(prj)
        mappings.write_to_object(prj)

    @classmethod
    def incremental_update_taxo_stats(cls, session: Session, prj_id: int, collated_changes: Dict):
        """
            Do not recompute the full stats for a project (which can be long).
            Instead, apply deltas because in this context we know them.
            TODO: All SQL to SQLAlchemy form
        """
        needed_ids = list(collated_changes.keys())
        # Lock taxo lines to prevent re-entering, during validation it's often a handful of them.
        pts_sql = """SELECT id
                       FROM taxonomy
                      WHERE id = ANY(:ids)
                     FOR NO KEY UPDATE
        """
        session.execute(pts_sql, {"ids": needed_ids})
        # Lock the rows we are going to update
        pts_sql = """SELECT id
                       FROM projects_taxo_stat 
                      WHERE projid = :prj
                        AND id = ANY(:ids) 
                     FOR NO KEY UPDATE"""
        res = session.execute(pts_sql, {"prj": prj_id, "ids": needed_ids})
        ids_in_db = set([classif_id for (classif_id,) in res.fetchall()])
        ids_not_in_db = set(needed_ids).difference(ids_in_db)
        if len(ids_not_in_db) > 0:
            pts_ins = """INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p) 
                         SELECT :prj, classif_id, count(*) nbr, 
                                COUNT(CASE WHEN classif_qual = 'V' THEN 1 END) nbr_v,
                                COUNT(CASE WHEN classif_qual = 'D' THEN 1 END) nbr_d,
                                COUNT(CASE WHEN classif_qual = 'P' THEN 1 END) nbr_p
                           FROM obj_head
                          WHERE projid = :prj AND classif_id = ANY(:ids)
                       GROUP BY classif_id"""
            session.execute(pts_ins, {'prj': prj_id, 'ids': list(ids_not_in_db)})
            if -1 in ids_not_in_db:
                # I guess, special case for unclassified
                pts_ins = """INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p) 
                             SELECT :prj, -1, count(*) nbr, 
                                    COUNT(CASE WHEN classif_qual = 'V' THEN 1 END) nbr_v,
                                    COUNT(CASE WHEN classif_qual = 'D' THEN 1 END) nbr_d,
                                    COUNT(CASE WHEN classif_qual = 'P' THEN 1 END) nbr_p
                               FROM obj_head
                              WHERE projid = :prj AND classif_id IS NULL"""
                session.execute(pts_ins, {'prj': prj_id})
        # Apply delta
        for classif_id, chg in collated_changes.items():
            if classif_id in ids_not_in_db:
                # The line was created with OK values
                continue
            sqlparam = {'prj': prj_id, 'cid': classif_id,
                        'nul': chg['n'], 'val': chg['V'], 'dub': chg['D'], 'prd': chg['P']}
            ts_sql = """UPDATE projects_taxo_stat 
                           SET nbr=nbr+:nul, nbr_v=nbr_v+:val, nbr_d=nbr_d+:dub, nbr_p=nbr_p+:prd 
                         where projid = :prj AND id = :cid"""
            session.execute(ts_sql, sqlparam)
