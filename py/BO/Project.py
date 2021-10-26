# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import typing
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Iterable, Optional, Union, Generator, Tuple

from BO.Classification import ClassifIDListT
from BO.Instrument import DescribedInstrumentSet
from BO.Mappings import RemapOp, MappedTableTypeT, ProjectMapping, TableMapping
from BO.Prediction import DeepFeatures
from BO.ProjectPrivilege import ProjectPrivilegeBO
from BO.User import MinimalUserBO, UserActivity, UserIDT
from BO.helpers.DataclassAsDict import DataclassAsDict
from DB import ObjectHeader, Sample, ProjectPrivilege, User, Project, ObjectFields, Acquisition, Process, \
    ParticleProject, ParticleCategoryHistogramList, ParticleSample, ParticleCategoryHistogram, ObjectsClassifHisto
from DB.Object import VALIDATED_CLASSIF_QUAL, PREDICTED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL
from DB.Project import ProjectIDT, ProjectIDListT
from DB.User import Role
from DB.helpers import Session, Result
from DB.helpers.Direct import text
from DB.helpers.ORM import Delete, Query, any_, and_, subqueryload, minimal_table_of, func
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


@dataclass(init=False)
class ProjectTaxoStats(DataclassAsDict):
    """
        Taxonomy statistics for a project.
    """
    projid: ProjectIDT
    used_taxa: ClassifIDListT
    nb_unclassified: int
    nb_validated: int
    nb_dubious: int
    nb_predicted: int


@dataclass(init=False)
class ProjectUserStats(DataclassAsDict):
    """
        User statistics for a project.
    """
    projid: ProjectIDT
    annotators: List[MinimalUserBO]
    activities: List[UserActivity]


# noinspection SqlDialectInspection
class ProjectBO(object):
    """
        A Project business object. So far (but less and less...) mainly a container
        for static API_operations involving it.
    """
    __slots__ = ["_project", "instrument", "highest_right",
                 "obj_free_cols", "sample_free_cols",
                 "acquisition_free_cols", "process_free_cols",
                 "init_classif_list",
                 "contact", "viewers", "annotators", "managers"]

    def __init__(self, project: Project):
        self._project = project
        # Added values
        self.instrument = ""
        self.highest_right = ""  # This field depends on the user asking for the information
        self.obj_free_cols: Dict[str, str] = {}
        self.sample_free_cols: Dict[str, str] = {}
        self.acquisition_free_cols: Dict[str, str] = {}
        self.process_free_cols: Dict[str, str] = {}
        self.init_classif_list: List[int] = []
        # Involved members
        self.contact: Optional[User] = None
        self.viewers: List[User] = []
        self.annotators: List[User] = []
        self.managers: List[User] = []

    def get_preset(self) -> ClassifIDListT:
        """
            Return the list of preset classification IDs.
        """
        if not self._project:
            return []
        init_list = self._project.initclassiflist
        if not init_list:
            return []
        return [int(cl_id) for cl_id in init_list.split(",")]

    def enrich(self):
        """
            Add DB fields and relations as (hopefully more) meaningful attributes
        """
        # Decode mappings to avoid exposing internal field
        mappings = ProjectMapping().load_from_project(self._project)
        self.obj_free_cols = mappings.object_mappings.tsv_cols_to_real
        self.sample_free_cols = mappings.sample_mappings.tsv_cols_to_real
        self.acquisition_free_cols = mappings.acquisition_mappings.tsv_cols_to_real
        self.process_free_cols = mappings.process_mappings.tsv_cols_to_real
        # Decode text list into numerical
        db_list = self._project.initclassiflist
        db_list = db_list if db_list else ""
        self.init_classif_list = [int(x) for x in db_list.split(",") if x.isdigit()]
        # Dispatch members by right
        by_right_fct = {ProjectPrivilegeBO.MANAGE: self.managers.append,
                        ProjectPrivilegeBO.ANNOTATE: self.annotators.append,
                        ProjectPrivilegeBO.VIEW: self.viewers.append}
        a_priv: ProjectPrivilege
        # noinspection PyTypeChecker
        for a_priv in self._project.privs_for_members:  # Use ORM to navigate in relationship
            priv_user = a_priv.user
            if priv_user is None:  # TODO: There is a line with NULL somewhere in DB
                continue
            if not priv_user.active:
                continue
            # noinspection PyTypeChecker
            by_right_fct[a_priv.privilege](priv_user)
            if 'C' == a_priv.extra:
                self.contact = priv_user
        return self

    def update(self, session: Session, title: str, visible: bool, status: str, description: str,
               init_classif_list: List[int],
               classiffieldlist: str, popoverfieldlist: str,
               cnn_network_id: str, comments: str,
               contact: Any,
               managers: List[Any], annotators: List[Any], viewers: List[Any],
               license_: str):
        assert contact is not None, "A valid Contact is needed."
        proj_id = self._project.projid
        # Field reflexes
        if cnn_network_id != self._project.cnn_network_id:
            # Delete CNN features which depend on the CNN network
            DeepFeatures.delete_all(session, proj_id)
        # Fields update
        self._project.title = title
        self._project.visible = visible
        self._project.status = status
        self._project.description = description
        self._project.classiffieldlist = classiffieldlist
        self._project.popoverfieldlist = popoverfieldlist
        self._project.cnn_network_id = cnn_network_id
        self._project.comments = comments
        self._project.license = license_
        # Inverse for extracted values
        self._project.initclassiflist = ",".join([str(cl_id) for cl_id in init_classif_list])
        # Inverse for users by privilege
        # Dispatch members by right
        # TODO: Nothing prevents or cares about redundant rights, such as adding same
        #     user as both Viewer and Annotator.
        by_right = {ProjectPrivilegeBO.MANAGE: managers,
                    ProjectPrivilegeBO.ANNOTATE: annotators,
                    ProjectPrivilegeBO.VIEW: viewers}
        # Remove all to avoid tricky diffs
        session.query(ProjectPrivilege). \
            filter(ProjectPrivilege.projid == proj_id).delete()
        # Add all
        contact_used = False
        for a_right, a_user_list in by_right.items():
            for a_user in a_user_list:
                # Set flag for contact person
                extra = None
                if a_user.id == contact.id and a_right == ProjectPrivilegeBO.MANAGE:
                    extra = 'C'
                    contact_used = True
                session.add(ProjectPrivilege(projid=proj_id,
                                             member=a_user.id,
                                             privilege=a_right,
                                             extra=extra))
        # Sanity check
        assert contact_used, "Could not set Contact, the designated user is not in Managers list."
        session.commit()

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Project field somehow then return it """
        return getattr(self._project, item)

    def get_all_num_columns_values(self, session: Session):
        """
            Get all numerical free fields values for all objects in a project.
        """
        from DB.helpers.ORM import MetaData
        metadata = MetaData(bind=session.get_bind())
        # TODO: Cache in a member
        mappings = ProjectMapping().load_from_project(self._project)
        num_fields_cols = set([col for col in mappings.object_mappings.tsv_cols_to_real.values()
                               if col[0] == 'n'])
        obj_fields_tbl = minimal_table_of(metadata, ObjectFields, num_fields_cols, exact_floats=True)
        qry: Query = session.query(Project)
        qry = qry.join(Project.all_samples).join(Sample.all_acquisitions).join(Acquisition.all_objects)
        qry = qry.join(obj_fields_tbl, ObjectHeader.objid == obj_fields_tbl.c.objfid)
        qry = qry.filter(Project.projid == self._project.projid)
        qry = qry.order_by(Acquisition.acquisid)
        qry = qry.with_entities(Acquisition.acquisid, Acquisition.orig_id, obj_fields_tbl)
        return qry.all()

    @staticmethod
    def update_taxo_stats(session: Session, projid: int):
        sql = text("""
        DELETE FROM projects_taxo_stat pts
         WHERE pts.projid = :prjid;
        INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p) 
        SELECT sam.projid, COALESCE(obh.classif_id, -1) id, COUNT(*) nbr, 
               COUNT(CASE WHEN obh.classif_qual = '""" + VALIDATED_CLASSIF_QUAL + """' THEN 1 END) nbr_v,
               COUNT(CASE WHEN obh.classif_qual = '""" + DUBIOUS_CLASSIF_QUAL + """' THEN 1 END) nbr_d, 
               COUNT(CASE WHEN obh.classif_qual = '""" + PREDICTED_CLASSIF_QUAL + """' THEN 1 END) nbr_p
          FROM obj_head obh
          JOIN acquisitions acq ON acq.acquisid = obh.acquisid 
          JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = :prjid 
        GROUP BY sam.projid, obh.classif_id;""")
        session.execute(sql, {'prjid': projid})

    @staticmethod
    def update_stats(session: Session, projid: int):
        sql = text("""
        UPDATE projects
           SET objcount=tsp.nbr_sum, 
               pctclassified=100.0*nbrclassified/tsp.nbr_sum, 
               pctvalidated=100.0*nbrvalidated/tsp.nbr_sum
          FROM projects prj
          LEFT JOIN
             (SELECT projid, SUM(nbr) nbr_sum, SUM(CASE WHEN id>0 THEN nbr END) nbrclassified, SUM(nbr_v) nbrvalidated
                FROM projects_taxo_stat
               WHERE projid = :prjid
              GROUP BY projid) tsp ON prj.projid = tsp.projid
        WHERE projects.projid = :prjid 
          AND prj.projid = :prjid""")
        session.execute(sql, {'prjid': projid})

    @staticmethod
    def read_taxo_stats(session: Session,
                        prj_ids: ProjectIDListT,
                        taxa_ids: Union[str, ClassifIDListT]) -> List[ProjectTaxoStats]:
        sql = """
        SELECT pts.projid, ARRAY_AGG(pts.id) as ids, 
               SUM(CASE WHEN pts.id = -1 THEN pts.nbr ELSE 0 END) as nb_u, 
               SUM(pts.nbr_v) as nb_v, SUM(pts.nbr_d) as nb_d, SUM(pts.nbr_p) as nb_p
          FROM projects_taxo_stat pts
         WHERE pts.projid = ANY(:ids)"""
        params: Dict[str, Any] = {'ids': prj_ids}
        if len(taxa_ids) > 0:
            if taxa_ids == 'all':
                pass
            else:
                sql += " AND pts.id = ANY(:tids)"
                params["tids"] = taxa_ids
        sql += """
        GROUP BY pts.projid"""
        if len(taxa_ids) > 0:
            sql += ", pts.id"
        res: Result = session.execute(text(sql), params)
        with CodeTimer("stats for %d projects:" % len(prj_ids), logger):
            ret = [ProjectTaxoStats(rec) for rec in res.fetchall()]
        for a_stat in ret:
            a_stat.used_taxa.sort()
        return ret

    @staticmethod
    def read_user_stats(session: Session, prj_ids: ProjectIDListT) -> List[ProjectUserStats]:
        """
            Read the users (annotators) involved in each project.
            Also compute a summary of their activity. This can only be an estimate since, e.g.
            imported data contains exact same data as the one obtained from live actions.
        """
        # Activity count: Count 1 for present classification for a user per object.
        #  Of course, the classification date is the latest for the user.
        pqry: Query = session.query(Project.projid, User.id, User.name,
                                    func.count(ObjectHeader.objid),
                                    func.max(ObjectHeader.classif_when))
        pqry = pqry.join(Sample).join(Acquisition).join(ObjectHeader)
        pqry = pqry.join(User, User.id == ObjectHeader.classif_who)
        pqry = pqry.filter(Project.projid == any_(prj_ids))
        pqry = pqry.filter(ObjectHeader.classif_who == User.id)
        pqry = pqry.group_by(Project.projid, User.id)
        pqry = pqry.order_by(Project.projid, User.name)
        ret = []
        user_activities: Dict[UserIDT, UserActivity] = {}
        user_activities_per_project = {}
        stats_per_project = {}
        with CodeTimer("user present stats for %d projects, qry: %s:" % (len(prj_ids), str(pqry)), logger):
            last_prj = None
            for projid, user_id, user_name, cnt, last_date in pqry.all():
                last_date_str = last_date.replace(microsecond=0).isoformat()
                if projid != last_prj:
                    last_prj = projid
                    prj_stat = ProjectUserStats((projid, [], []))
                    ret.append(prj_stat)
                    user_activities = {}
                    # Store for second pass with history
                    stats_per_project[projid] = prj_stat
                    user_activities_per_project[projid] = user_activities
                prj_stat.annotators.append(MinimalUserBO((user_id, user_name)))
                user_activity = UserActivity((user_id, cnt, last_date_str))
                prj_stat.activities.append(user_activity)
                # Store for second pass
                user_activities[user_id] = user_activity
        # Activity count update: Add 1 for each entry in history for each user.
        # The dates in history are ignored, except for users which do not appear in first resultset.
        hqry: Query = session.query(Project.projid, User.id, User.name,
                                    func.count(ObjectsClassifHisto.objid),
                                    func.max(ObjectsClassifHisto.classif_date))
        hqry = hqry.join(Sample).join(Acquisition).join(ObjectHeader).join(ObjectsClassifHisto)
        hqry = hqry.join(User, User.id == ObjectsClassifHisto.classif_who)
        hqry = hqry.filter(Project.projid == any_(prj_ids))
        hqry = hqry.group_by(Project.projid, User.id)
        hqry = hqry.order_by(Project.projid, User.name)
        with CodeTimer("user history stats for %d projects, qry: %s:" % (len(prj_ids), str(hqry)), logger):
            last_prj = None
            for projid, user_id, user_name, cnt, last_date in hqry.all():
                last_date_str = last_date.replace(microsecond=0).isoformat()
                if projid != last_prj:
                    last_prj = projid
                    # Just in case
                    if projid not in user_activities_per_project:
                        continue
                    # Get stored data for the project
                    user_activities = user_activities_per_project[projid]
                    prj_stat = stats_per_project[projid]
                already_there = user_activities.get(user_id)
                if already_there is not None:
                    # A user in both history and present classification
                    already_there.nb_actions += cnt
                else:
                    # A user _only_ in history
                    prj_stat.annotators.append(MinimalUserBO((user_id, user_name)))
                    user_activity = UserActivity((user_id, cnt, last_date_str))
                    prj_stat.activities.append(user_activity)
                    user_activities[user_id] = user_activity
        return ret

    @staticmethod
    def projects_for_user(session: Session, user: User,
                          for_managing: bool = False,
                          not_granted: bool = False,
                          title_filter: str = '',
                          instrument_filter: str = '',
                          filter_subset: bool = False) -> List[ProjectIDT]:
        """
        :param session:
        :param user: The user for which the list is needed.
        :param for_managing: If set, list the projects that the user can manage.
        :param not_granted: If set, list (only) the projects on which given user has no right, so user can
                                request access to them.
        :param title_filter: If set, filter out the projects with title not matching the required string,
                                or if set to a number, filter out the projects of which ID does not match.
        :param instrument_filter: If set, filter out the projects which do not have given instrument in at least
                                     one sample.
        :param filter_subset: If set, filter out any project of which title contains 'subset'.
        :return: The project IDs
        """
        sql_params: Dict[str, Any] = {"user_id": user.id}

        # Default query: all projects, eventually with first manager information
        # noinspection SqlResolve
        sql = """SELECT prj.projid
               FROM projects prj
               LEFT JOIN ( """ + ProjectPrivilegeBO.first_manager_by_project() + """ ) fpm 
                      ON fpm.projid = prj.projid """
        if not_granted:
            if not user.has_role(Role.APP_ADMINISTRATOR):
                # Add the projects for which no entry is found in ProjectPrivilege
                sql += """
                       LEFT JOIN projectspriv prp ON prj.projid = prp.projid AND prp.member = :user_id
                      WHERE prp.member is null 
                        AND prj.visible """
                if for_managing:
                    # No right so no possibility to manage
                    sql += " AND False "
            else:
                # Admin can see all, so nothing is not granted to Admin
                sql += " WHERE False "
        else:
            if not user.has_role(Role.APP_ADMINISTRATOR):
                # Not an admin, so restrict to projects which current user can work on, or view
                sql += """
                        JOIN projectspriv prp 
                          ON prj.projid = prp.projid 
                         AND prp.member = :user_id """
                if for_managing:
                    sql += """
                         AND prp.privilege = '%s' """ % ProjectPrivilegeBO.MANAGE
            sql += " WHERE 1 = 1 "

        if title_filter != '':
            sql += """ 
                    AND ( prj.title ILIKE '%%'|| :title ||'%%'
                          OR TO_CHAR(prj.projid,'999999') LIKE '%%'|| :title ) """
            sql_params["title"] = title_filter

        if instrument_filter != '':
            sql += """
                     AND prj.projid IN (SELECT DISTINCT sam.projid FROM samples sam, acquisitions acq
                                         WHERE acq.acq_sample_id = sam.sampleid
                                           AND acq.instrument ILIKE '%%'|| :instrum ||'%%' ) """
            sql_params["instrum"] = instrument_filter

        if filter_subset:
            sql += """
                     AND NOT prj.title ILIKE '%%subset%%'  """

        with CodeTimer("Projects.projects_for_user query (ids):", logger):
            res: Result = session.execute(text(sql), sql_params)
            # single-element tuple :( DBAPI
            ret = [an_id for an_id, in res.fetchall()]
        return ret  # type:ignore

    @staticmethod
    def list_public_projects(session: Session,
                             title_filter: str = '') -> List[ProjectIDT]:
        """
        :param session:
        :param title_filter: If set, filter out the projects with title not matching the required string.
        :return: The project IDs
        """
        pattern = '%' + title_filter + '%'
        qry: Query = session.query(Project.projid)
        qry = qry.filter(Project.visible)
        qry = qry.filter(Project.title.ilike(pattern))
        ret = [an_id for an_id, in qry.all()]
        return ret

    @classmethod
    def get_bounding_geo(cls, session: Session, project_ids: ProjectIDListT) -> Iterable[float]:
        # TODO: Why using the view?
        sql = ("SELECT min(o.latitude), max(o.latitude), min(o.longitude), max(o.longitude)"
               "  FROM objects o "
               " WHERE o.projid = ANY(:prj)")
        res: Result = session.execute(text(sql), {"prj": project_ids})
        vals = res.first()
        assert vals
        return [a_val for a_val in vals]

    @classmethod
    def get_date_range(cls, session: Session, project_ids: ProjectIDListT) -> Iterable[datetime]:
        # TODO: Why using the view?
        sql = ("SELECT min(o.objdate), max(o.objdate)"
               "  FROM objects o "
               " WHERE o.projid = ANY(:prj)")
        res: Result = session.execute(text(sql), {"prj": project_ids})
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
        Sample.propagate_geo(session, prj_id)
        ProjectBO.update_taxo_stats(session, prj_id)
        # Stats depend on taxo stats
        ProjectBO.update_stats(session, prj_id)

    @classmethod
    def delete_object_parents(cls, session: Session, prj_id: int) -> List[int]:
        """
            Remove object parents, also project children entities, in the project.
        """
        # The EcoTaxa samples which are going to disappear. We have to cleanup Particle side.
        soon_deleted_samples: Query = Query(Sample.sampleid).filter(Sample.projid == prj_id)
        # The EcoPart samples to clean.
        soon_invalid_part_samples: Query = Query(ParticleSample.psampleid).filter(
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
        del_acquis_qry: Delete = Acquisition.__table__. \
            delete().where(Acquisition.acq_sample_id.in_(soon_deleted_samples))
        logger.info("Del acquisitions :%s", str(del_acquis_qry))
        gone_acqs = session.execute(del_acquis_qry).rowcount
        ret.append(gone_acqs)
        logger.info("%d rows deleted", gone_acqs)

        del_sample_qry: Delete = Sample.__table__. \
            delete().where(Sample.sampleid.in_(soon_deleted_samples))
        logger.info("Del samples :%s", str(del_sample_qry))
        gone_sams = session.execute(del_sample_qry).rowcount
        ret.append(gone_sams)
        logger.info("%d rows deleted", gone_sams)

        ret.append(gone_acqs)
        session.commit()
        return ret

    @staticmethod
    def delete(session: Session, prj_id: int):
        """
            Completely remove the project. It is assumed that contained objects have been removed.
        """
        # TODO: Remove from user preferences
        # Unlink Particle project if any
        upd_qry = ParticleProject.__table__.update().where(ParticleProject.projid == prj_id).values(projid=None)
        row_count = session.execute(upd_qry).rowcount
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
        # Do the remapping, including blanking of unused columns
        values = {a_remap.to: text(a_remap.frm) if a_remap.frm is not None else a_remap.frm
                  for a_remap in remaps}
        qry: Query = session.query(table)
        samples_4_prj: Query
        acqs_4_samples: Query
        if table == Sample:
            qry = qry.filter(Sample.projid == prj_id)  # type: ignore
        elif table == Acquisition:
            samples_4_prj = Query(Sample.sampleid).filter(Sample.projid == prj_id)
            qry = qry.filter(Acquisition.acq_sample_id.in_(samples_4_prj))  # type: ignore
        elif table == Process:
            samples_4_prj = Query(Sample.sampleid).filter(Sample.projid == prj_id)
            acqs_4_samples = Query(Acquisition.acquisid).filter(Acquisition.acq_sample_id.in_(samples_4_prj))
            qry = qry.filter(Process.processid.in_(acqs_4_samples))  # type: ignore
        elif table == ObjectFields:
            samples_4_prj = Query(Sample.sampleid).filter(Sample.projid == prj_id)
            acqs_4_samples = Query(Acquisition.acquisid).filter(Acquisition.acq_sample_id.in_(samples_4_prj))
            objs_for_acqs: Query = Query(ObjectHeader.objid).filter(ObjectHeader.acquisid.in_(acqs_4_samples))
            qry = qry.filter(ObjectFields.objfid.in_(objs_for_acqs))  # type: ignore
        qry = qry.update(values=values, synchronize_session=False)

        logger.info("Remap query for %s: %s", table.__tablename__, qry)

    @classmethod
    def get_all_object_ids(cls, session: Session,
                           prj_id: int):  # TODO: Problem with recursive import -> ObjetIdListT:
        """
            Return the full list of objects IDs inside a project.
            TODO: Maybe better in ObjectBO
        """
        qry: Query = session.query(ObjectHeader.objid)
        qry = qry.join(Acquisition, Acquisition.acquisid == ObjectHeader.acquisid)
        qry = qry.join(Sample, and_(Sample.sampleid == Acquisition.acq_sample_id,
                                    Sample.projid == prj_id))
        return [an_id for an_id, in qry.all()]

    @classmethod
    def get_all_object_ids_with_first_image(cls, session: Session, prj_id: int) -> Dict[Any, str]:  # ObjectIDT
        """
            Return the full list of objects IDs and first image file name inside a project.
        """
        sql = text("""
    SELECT obh.objid, img.file_name
      FROM obj_head obh
      JOIN images img ON obh.objid = img.objid 
                     AND img.imgrank = (SELECT MIN(img3.imgrank) FROM images img3 WHERE img3.objid = obh.objid)
      JOIN acquisitions acq ON acq.acquisid = obh.acquisid 
      JOIN samples sam ON sam.sampleid = acq.acq_sample_id
     WHERE sam.projid = :prj""")
        res: Result = session.execute(sql, {"prj": prj_id})
        return {objid: file_name for (objid, file_name) in res.fetchall()}

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
        session.execute(text(pts_sql), {"ids": needed_ids})
        # Lock the rows we are going to update, including -1 for unclassified
        pts_sql = """SELECT id, nbr
                       FROM projects_taxo_stat 
                      WHERE projid = :prj
                        AND id = ANY(:ids)
                     FOR NO KEY UPDATE"""
        res = session.execute(text(pts_sql), {"prj": prj_id, "ids": needed_ids})
        ids_in_db = {classif_id: nbr for (classif_id, nbr) in res.fetchall()}
        ids_not_in_db = set(needed_ids).difference(ids_in_db.keys())
        if len(ids_not_in_db) > 0:
            # Insert rows for missing IDs
            # TODO: We can't lock what does not exists, so it can fail here.
            pts_ins = """INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p) 
                         SELECT :prj, COALESCE(obh.classif_id, -1), COUNT(*) nbr, 
                                COUNT(CASE WHEN obh.classif_qual = '""" + VALIDATED_CLASSIF_QUAL + """' THEN 1 END) nbr_v,
                                COUNT(CASE WHEN obh.classif_qual = '""" + DUBIOUS_CLASSIF_QUAL + """' THEN 1 END) nbr_d,
                                COUNT(CASE WHEN obh.classif_qual = '""" + PREDICTED_CLASSIF_QUAL + """' THEN 1 END) nbr_p
                           FROM obj_head obh
                           JOIN acquisitions acq ON acq.acquisid = obh.acquisid 
                           JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = :prj 
                          WHERE COALESCE(obh.classif_id, -1) = ANY(:ids)
                       GROUP BY obh.classif_id"""
            session.execute(text(pts_ins), {'prj': prj_id, 'ids': list(ids_not_in_db)})
        # Apply delta
        for classif_id, chg in collated_changes.items():
            if classif_id in ids_not_in_db:
                # The line was created just above, with OK values
                continue
            if ids_in_db[classif_id] + chg['n'] == 0:
                # The delta means 0 for this taxon in this project, delete the line
                sqlparam = {'prj': prj_id, 'cid': classif_id}
                ts_sql = """DELETE FROM projects_taxo_stat 
                             WHERE projid = :prj AND id = :cid"""
            else:
                # General case
                sqlparam = {'prj': prj_id, 'cid': classif_id,
                            'nul': chg['n'],
                            'val': chg[VALIDATED_CLASSIF_QUAL],
                            'dub': chg[DUBIOUS_CLASSIF_QUAL],
                            'prd': chg[PREDICTED_CLASSIF_QUAL]}
                ts_sql = """UPDATE projects_taxo_stat 
                               SET nbr=nbr+:nul, nbr_v=nbr_v+:val, nbr_d=nbr_d+:dub, nbr_p=nbr_p+:prd 
                             WHERE projid = :prj AND id = :cid"""
            session.execute(text(ts_sql), sqlparam)

    @classmethod
    def get_sort_fields(cls, project: Project) -> typing.OrderedDict[str, str]:
        """
            Return the content of 'Fields available for sorting & Display In the manual classification page'
        """
        # e.g. area=area [pixel]
        #      meangreyobjet=mean [0-255]
        #      fractal_box=fractal
        ret = OrderedDict()
        list_as_str = project.classiffieldlist
        if list_as_str is None:
            return ret
        for a_pair in list_as_str.splitlines():
            try:
                free_col, alias = a_pair.split("=")
            except ValueError:
                continue
            ret[free_col.strip()] = alias.strip()
        return ret

    @classmethod
    def get_sort_db_columns(cls, project: Project, mapping: Optional[TableMapping]) -> List[str]:
        """
            Get sort list as DB columns, e.g. typically t03, n34
        """
        sort_list = cls.get_sort_fields(project)
        if mapping is None:
            return []
        mpg = mapping.find_tsv_cols(list(sort_list.keys()))
        return list(mpg.values())


class ProjectBOSet(object):
    """
        Many projects...
    """

    def __init__(self, session: Session, prj_ids: ProjectIDListT, public: bool = False):
        # Query the project and ORM-load neighbours as well, as they will be needed in enrich()
        qry: Query = session.query(Project)
        qry = qry.options(subqueryload(Project.privs_for_members))
        qry = qry.options(subqueryload(Project.members))
        qry = qry.filter(Project.projid == any_(prj_ids))
        self.projects: List[ProjectBO] = []
        # De-duplicate
        projs = []
        with CodeTimer("%s BO projects query:" % len(prj_ids), logger):
            for a_proj in qry.all():
                projs.append(a_proj)
        # Build BOs and enrich
        with CodeTimer("%s BO projects init:" % len(projs), logger):
            self_projects_append = self.projects.append
            for a_proj in projs:
                if public:
                    self_projects_append(ProjectBO(a_proj))
                else:
                    self_projects_append(ProjectBO(a_proj).enrich())
        # Add instruments
        with CodeTimer("%s set instruments:" % len(prj_ids), logger):
            instruments = DescribedInstrumentSet(session, prj_ids)
            for a_project in self.projects:
                instrums = instruments.by_project.get(a_project.projid)
                if instrums is not None:
                    a_project.instrument = ",".join(instrums)

    def as_list(self) -> List[ProjectBO]:
        return self.projects

    @staticmethod
    def get_one(session: Session, prj_ids: ProjectIDT) -> Optional[ProjectBO]:
        """
            Get a single BO per its id
        """
        mini_set = ProjectBOSet(session, [prj_ids])
        if len(mini_set.projects) > 0:
            return mini_set.projects[0]
        else:
            return None
