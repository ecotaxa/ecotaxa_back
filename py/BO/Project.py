# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import typing
from enum import Enum
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import (
    List,
    Dict,
    Any,
    Iterable,
    Optional,
    Union,
    OrderedDict as OrderedDictT,
    Set,
    Tuple,
    cast,
    Final,
)

from BO.Classification import ClassifIDListT
from BO.Mappings import (
    RemapOp,
    MappedTableTypeT,
    ProjectMapping,
    TableMapping,
    ProjectSetMapping,
)
from BO.Prediction import DeepFeatures
from BO.ProjectPrivilege import ProjectPrivilegeBO
from BO.DataLicense import AccessLevelEnum
from BO.ProjectVars import ProjectVar
from BO.Rights import RightsBO, Action
from BO.SpaceTime import USED_FIELDS_FOR_SUNPOS, compute_sun_position
from BO.User import (
    MinimalUserBO,
    ContactUserListT,
    UserActivity,
    MinimalUserBOListT,
    UserActivityListT,
)
from DB.Acquisition import Acquisition
from DB.Object import (
    VALIDATED_CLASSIF_QUAL,
    PREDICTED_CLASSIF_QUAL,
    DUBIOUS_CLASSIF_QUAL,
    ObjectsClassifHisto,
    ObjectHeader,
    ObjectFields,
)
from DB.Process import Process
from DB.Project import ProjectIDT, ProjectIDListT, Project
from DB.Collection import CollectionProject, Collection
from BO.Collection import MinimalCollectionBO
from BO.User import UserIDT, UserIDListT, ContactUserBO
from DB.ProjectPrivilege import ProjectPrivilege
from DB.ProjectVariables import KNOWN_PROJECT_VARS
from DB.ProjectVariables import ProjectVariables
from DB.Sample import Sample
from DB.User import Role, User, UserStatus
from DB.helpers import Session, Result
from DB.helpers.Bean import Bean
from DB.helpers.Core import select
from DB.helpers.Direct import text
from DB.helpers.ORM import (
    Delete,
    Query,
    any_,
    and_,
    subqueryload,
    joinedload,
    minimal_table_of,
    func,
)
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer
from helpers.FieldListType import FieldListType

logger = get_logger(__name__)

ChangeTypeT = Dict[int, Dict[str, int]]


class MappingColumnEnum(str, Enum):
    obj: Final = "mappingobj"
    sample: Final = "mappingsample"
    acq: Final = "mappingacq"
    process: Final = "mappingprocess"


@dataclass()
class ProjectTaxoStats:
    """
    Taxonomy statistics for a project.
    """

    projid: ProjectIDT
    used_taxa: ClassifIDListT
    nb_unclassified: int
    nb_validated: int
    nb_dubious: int
    nb_predicted: int


@dataclass()
class ProjectUserStats:
    """
    User statistics for a project.
    """

    projid: ProjectIDT
    annotators: MinimalUserBOListT
    activities: UserActivityListT


@dataclass()
class ProjectColumns:
    """
    Column value for specific columns.
    """

    projid: ProjectIDT
    columns: List[str]
    values: List[str]


# noinspection SqlDialectInspection
class ProjectBO(object):
    """
    A Project business object. So far (but less and less...) mainly a container
    for static API_operations involving it.
    """

    __slots__ = [
        "_project",
        "instrument",
        "instrument_url",
        "highest_right",
        "obj_free_cols",
        "sample_free_cols",
        "acquisition_free_cols",
        "process_free_cols",
        "init_classif_list",
        "bodc_variables",
        "contact",
        "viewers",
        "annotators",
        "managers",
    ]

    def __init__(self, project: Project):
        self._project = project
        # Added/copied values
        self.instrument = project.instrument_id
        self.instrument_url = None
        self.highest_right = (
            ""  # This field depends on the user asking for the information
        )
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
        # Formulas AKA variables, used to compute BODC quantities
        self.bodc_variables: Dict[str, str] = {}

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

    def enrich(self) -> "ProjectBO":
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
        by_right_fct = {
            ProjectPrivilegeBO.MANAGE: self.managers.append,
            ProjectPrivilegeBO.ANNOTATE: self.annotators.append,
            ProjectPrivilegeBO.VIEW: self.viewers.append,
        }
        a_priv: ProjectPrivilege
        # noinspection PyTypeChecker
        for (
            a_priv
        ) in self._project.privs_for_members:  # Use ORM to navigate in relationship
            priv_user = a_priv.user
            if priv_user is None:  # TODO: There is a line with NULL somewhere in DB
                continue
            if priv_user.status != UserStatus.active.value:
                continue
            assert a_priv.privilege is not None
            by_right_fct[a_priv.privilege](priv_user)
            if "C" == a_priv.extra:
                self.contact = priv_user
        self.instrument_url = self._project.instrument.bodc_url
        # Variables
        if self._project.variables is not None:
            self.bodc_variables.update(self._project.variables.to_dict())
        return self

    def public_enrich(self) -> "ProjectBO":
        """
        Enrichment with fields we can expose to public unauthenticated calls.
        """
        self.instrument_url = self._project.instrument.bodc_url
        return self

    def update(
        self,
        session: Session,
        instrument: Optional[str],
        title: str,
        visible: Optional[bool],
        status: Optional[str],
        description: Optional[str],
        init_classif_list: List[int],
        classiffieldlist: Optional[str],
        popoverfieldlist: Optional[str],
        cnn_network_id: Optional[str],
        comments: Optional[str],
        contact: Any,
        managers: List[Any],
        annotators: List[Any],
        viewers: List[Any],
        license_: Optional[str],
        bodc_vars: Dict,
        access:Optional[str],
        formulae:Optional[str]
    ):
        assert contact is not None, "A valid Contact is needed."
        proj_id = self._project.projid
        # strip title
        title = title.strip()
        assert instrument is not None, "A valid Instrument is needed."
        # Validate variables
        errors: List[str] = []
        for a_var, its_def in bodc_vars.items():
            if its_def is None or its_def.strip() == "":
                continue
            assert (
                a_var in KNOWN_PROJECT_VARS
            ), "Invalid project variable key: {}".format(a_var)
            try:
                _ = ProjectVar.from_project(a_var, its_def)
            except TypeError as e:
                errors.append("Error {} in formula '{}': ".format(str(e), its_def))
        assert len(errors) == 0, "There are formula errors: " + str(errors)
        # Field reflexes
        if cnn_network_id != self._project.cnn_network_id:
            # Delete CNN features, which depend on the CNN network
            DeepFeatures.delete_all(session, proj_id)
        # Fields update
        self._project.instrument_id = instrument
        self._project.title = title
        self._project.visible = visible
        self._project.status = status
        self._project.description = description
        self._project.classiffieldlist = classiffieldlist
        self._project.popoverfieldlist = popoverfieldlist
        self._project.cnn_network_id = cnn_network_id
        self._project.comments = comments
        self._project.license = license_
        self._project.access = access
        self._project.formulae = formulae
        # Inverse for extracted values
        self._project.initclassiflist = ",".join(
            [str(cl_id) for cl_id in init_classif_list]
        )
        # Inverse for users by privilege
        # Dispatch members by right
        # TODO: Nothing prevents or cares about redundant rights, such as adding same
        #     user as both Viewer and Annotator.
        by_right = {
            ProjectPrivilegeBO.MANAGE: managers,
            ProjectPrivilegeBO.ANNOTATE: annotators,
            ProjectPrivilegeBO.VIEW: viewers,
        }
        # Remove all to avoid tricky diffs
        session.query(ProjectPrivilege).filter(
            ProjectPrivilege.projid == proj_id
        ).delete()
        # Add all
        contact_used = False
        for a_right, a_user_list in by_right.items():
            for a_user in a_user_list:
                # Set flag for contact person
                extra = None
                if a_user.id == contact.id and a_right == ProjectPrivilegeBO.MANAGE:
                    extra = "C"
                    contact_used = True
                projectpriv=ProjectPrivilege()
                projectpriv.projid=proj_id
                projectpriv.member=a_user.id
                projectpriv.privilege=a_right
                projectpriv.extra=extra
                session.add(projectpriv)
        # Sanity check
        assert (
            contact_used
        ), "Could not set Contact, the designated user is not in Managers list."
        # Variables update, in full
        bodc_vars_model = self._project.variables
        if bodc_vars_model is None:
            # Create record if needed
            bodc_vars_model = ProjectVariables()
            self._project.variables = bodc_vars_model
        bodc_vars_model.load_from_dict(bodc_vars)
        session.commit()

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a Project field somehow then return it"""
        return getattr(self._project, item)

    def get_all_num_columns_values(self, session: Session):
        """
        Get all numerical free fields values for all objects in a project.
        """
        from DB.helpers.ORM import MetaData

        metadata = MetaData(bind=session.get_bind())
        # TODO: Cache in a member
        mappings = ProjectMapping().load_from_project(self._project)
        num_fields_cols = set(
            [
                col
                for col in mappings.object_mappings.tsv_cols_to_real.values()
                if col[0] == "n"
            ]
        )
        obj_fields_tbl = minimal_table_of(
            metadata, ObjectFields, num_fields_cols, exact_floats=True
        )
        qry = session.query(Project)
        qry = (
            qry.join(Project.all_samples)
            .join(Sample.all_acquisitions)
            .join(Acquisition.all_objects)
        )
        qry = qry.join(obj_fields_tbl, ObjectHeader.objid == obj_fields_tbl.c.objfid)
        qry = qry.filter(Project.projid == self._project.projid)
        qry = qry.order_by(Acquisition.acquisid)
        qry = qry.with_entities(
            Acquisition.acquisid, Acquisition.orig_id, obj_fields_tbl
        )
        return qry.all()

    @staticmethod
    def update_taxo_stats(session: Session, projid: int):
        sql = text(
            """
        DELETE FROM projects_taxo_stat pts
         WHERE pts.projid = :prjid;
        INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p)
        SELECT sam.projid, COALESCE(obh.classif_id, -1) id, COUNT(*) nbr,
               COUNT(CASE WHEN obh.classif_qual = '"""
            + VALIDATED_CLASSIF_QUAL
            + """' THEN 1 END) nbr_v,
               COUNT(CASE WHEN obh.classif_qual = '"""
            + DUBIOUS_CLASSIF_QUAL
            + """' THEN 1 END) nbr_d,
               COUNT(CASE WHEN obh.classif_qual = '"""
            + PREDICTED_CLASSIF_QUAL
            + """' THEN 1 END) nbr_p
          FROM %s obh
          JOIN acquisitions acq ON acq.acquisid = obh.acquisid
          JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = :prjid
        GROUP BY sam.projid, obh.classif_id;"""
            % ObjectHeader.__tablename__
        )
        session.execute(sql, {"prjid": projid})

    @staticmethod
    def update_stats(session: Session, projid: int):
        sql = text(
            """
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
          AND prj.projid = :prjid"""
        )
        session.execute(sql, {"prjid": projid})

    @staticmethod
    def read_taxo_stats(
        session: Session, prj_ids: ProjectIDListT, taxa_ids: Union[str, ClassifIDListT]
    ) -> List[ProjectTaxoStats]:
        sql = """
        SELECT pts.projid, ARRAY_AGG(pts.id) as used_taxa,
               SUM(CASE WHEN pts.id = -1 THEN pts.nbr ELSE 0 END) as nb_unclassified,
               SUM(pts.nbr_v) as nb_validated, SUM(pts.nbr_d) as nb_dubious, SUM(pts.nbr_p) as nb_predicted
          FROM projects_taxo_stat pts
         WHERE pts.projid = ANY(:ids)"""
        params: Dict[str, Any] = {"ids": prj_ids}
        if len(taxa_ids) > 0:
            if taxa_ids == "all":
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
            ret = [ProjectTaxoStats(**rec) for rec in res]  # type:ignore # case4
        for a_stat in ret:
            a_stat.used_taxa.sort()
        return ret

    @staticmethod
    def validated_categories_ids(
        session: Session, prj_ids: ProjectIDListT
    ) -> ClassifIDListT:
        """Return display_name for all categories with at least one validated object,
        in provided project list."""
        qry = session.query(ObjectHeader.classif_id).distinct(ObjectHeader.classif_id)
        qry = qry.join(Acquisition).join(Sample).join(Project)
        qry = qry.filter(Project.projid == any_(prj_ids))
        qry = qry.filter(ObjectHeader.classif_qual == VALIDATED_CLASSIF_QUAL)
        with CodeTimer(
            "Validated category IDs for %s, qry: %s " % (len(prj_ids), str(qry)), logger
        ):
            return [an_id for an_id, in qry]

    @staticmethod
    def all_samples_orig_id(session: Session, prj_ids: ProjectIDListT) -> Set[Tuple]:
        """Return orig_id (i.e. users' sample_id) for all projects.
        If several projects, it is assumed that project ids come from a Collection, so no naming conflict.
        """
        # TODO: Test that there is indeed no collision, count(project_id) should be 1
        qry = session.query(Sample.orig_id).distinct(Sample.orig_id)
        qry = qry.join(Project)
        qry = qry.filter(Project.projid == any_(prj_ids))
        return set([(an_id,) for an_id, in qry])

    @staticmethod
    def all_subsamples_orig_id(session: Session, prj_ids: ProjectIDListT) -> Set[Tuple]:
        """Return Sample orig_id (i.e. users' sample_id) and Acquisition orig_id (i.e. users' acq_id) pairs
        for all projects. If several projects, it is assumed that project ids come from a Collection,
        so no naming conflict."""
        # TODO: Test that there is indeed no collision, count(project_id) should be 1
        qry = session.query(Sample.orig_id, Acquisition.orig_id).distinct()
        qry = qry.join(Project)
        qry = qry.filter(Sample.sampleid == Acquisition.acq_sample_id)
        qry = qry.filter(Project.projid == any_(prj_ids))
        return set([(sam_id, acq_id) for sam_id, acq_id in qry])

    @staticmethod
    def read_user_stats(
        session: Session, prj_ids: ProjectIDListT
    ) -> List[ProjectUserStats]:
        """
        Read the users (annotators) involved in each project.
        Also compute a summary of their activity. This can only be an estimate since, e.g.
        imported data contains exact same data as the one obtained from live actions.
        """
        # Activity count: Count 1 for present classification for a user per object.
        #  Of course, the classification date is the latest for the user.
        pqry = session.query(
            Project.projid,
            User.id,
            User.name,
            func.count(ObjectHeader.objid),
            func.max(
                ObjectHeader.classif_date
            ),  # OK we filter manual action via user id below
        )
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
        with CodeTimer(
            "user present stats for %d projects, qry: %s:" % (len(prj_ids), str(pqry)),
            logger,
        ):
            last_prj: Optional[int] = None
            prj_stat = ProjectUserStats(0, [], [])
            for projid, user_id, user_name, cnt, last_date in pqry:
                if last_date is None:
                    continue
                last_date_str = last_date.replace(microsecond=0).isoformat()
                if projid != last_prj:
                    last_prj = projid
                    prj_stat = ProjectUserStats(projid, [], [])
                    ret.append(prj_stat)
                    user_activities = {}
                    # Store for second pass with history
                    stats_per_project[projid] = prj_stat
                    user_activities_per_project[projid] = user_activities
                prj_stat.annotators.append(MinimalUserBO(user_id, user_name))
                user_activity = UserActivity(user_id, cnt, last_date_str)
                prj_stat.activities.append(user_activity)
                # Store for second pass
                user_activities[user_id] = user_activity
        # Activity count update: Add 1 for each entry in history for each user.
        # The dates in history are ignored, except for users which do not appear in first resultset.
        hqry = session.query(
            Project.projid,
            User.id,
            User.name,
            func.count(ObjectsClassifHisto.objid),
            func.max(ObjectsClassifHisto.classif_date),
        )
        hqry = (
            hqry.join(Sample)
            .join(Acquisition)
            .join(ObjectHeader)
            .join(ObjectsClassifHisto)
        )
        hqry = hqry.join(User, User.id == ObjectsClassifHisto.classif_who)
        hqry = hqry.filter(Project.projid == any_(prj_ids))
        hqry = hqry.group_by(Project.projid, User.id)
        hqry = hqry.order_by(Project.projid, User.name)
        with CodeTimer(
            "user history stats for %d projects, qry: %s:" % (len(prj_ids), str(hqry)),
            logger,
        ):
            last_prj = None
            for projid, user_id, user_name, cnt, last_date in hqry:
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
                    prj_stat.annotators.append(MinimalUserBO(user_id, user_name))
                    user_activity = UserActivity(user_id, cnt, last_date_str)
                    prj_stat.activities.append(user_activity)
                    user_activities[user_id] = user_activity
        return ret

    @staticmethod
    def projects_for_user(
        session: Session,
        user: User,
        for_managing: bool = False,
        not_granted: bool = False,
        title_filter: str = "",
        instrument_filter: str = "",
        filter_subset: bool = False,
    ) -> List[ProjectIDT]:
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
        sql = (
            """SELECT prj.projid
                       FROM projects prj
                       LEFT JOIN ( """
            + ProjectPrivilegeBO.first_manager_by_project()
            + """ ) fpm
                      ON fpm.projid = prj.projid """
        )
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
                    sql += (
                        """
                                 AND prp.privilege = '%s' """
                        % ProjectPrivilegeBO.MANAGE
                    )
            sql += " WHERE 1 = 1 "

        if title_filter != "":
            sql += """
                    AND ( prj.title ILIKE '%%'|| :title ||'%%'
                          OR TO_CHAR(prj.projid,'999999') LIKE '%%'|| :title ) """
            sql_params["title"] = title_filter

        if instrument_filter != "":
            sql += """
                     AND prj.instrument_id ILIKE '%%'|| :instrum ||'%%' """
            sql_params["instrum"] = instrument_filter

        if filter_subset:
            sql += """
                     AND NOT prj.title ILIKE '%%subset%%'  """

        with CodeTimer("Projects.projects_for_user query (ids):", logger):
            res: Result = session.execute(text(sql), sql_params)
            # single-element tuple :( DBAPI
            ret = [an_id for an_id, in res.fetchall()]
        return ret

    @staticmethod
    def list_public_projects(
        session: Session, title_filter: str = ""
    ) -> List[ProjectIDT]:
        """
        :param session:
        :param title_filter: If set, filter out the projects with title not matching the required string.
        :return: The project IDs
        """
        pattern = "%" + title_filter + "%"
        qry = session.query(Project.projid)
        qry = qry.filter(Project.visible)
        qry = qry.filter(Project.title.ilike(pattern))
        ret = [an_id for an_id, in qry]
        return ret

    @staticmethod
    def in_collections(session: Session, projid: int) -> List[MinimalCollectionBO]:
        """
        :param session:
        :param projid:
        :return: The collection IDs the project belongs to.
        """
        qry = (
            session.query(
                Collection.id,
                Collection.external_id,
                Collection.title,
                Collection.short_title,
                Collection.provider_user_id,
                Collection.contact_user_id,
                User.name,
                User.email,
                User.orcid,
                User.organisation,
            )
            .join(Collection.contact_user)
            .join(CollectionProject)
            .where(CollectionProject.project_id == projid)
        )
        ret = []
        for r in qry:
            #if r.contact_user_id:
                #contact = ContactUserBO(id=r.contact_user_id,email=r.email,name=r.name, orcid=r.orcid or "None",organisation=r.organisation)
            #else:
               #contact = None
            qry_proj = session.query(CollectionProject.project_id).where(
                CollectionProject.collection_id == r.id
            )
            project_ids = [p.project_id for p in qry_proj]

            ret.append(
                MinimalCollectionBO(
                    id=r.id,
                    external_id=r.external_id or None,
                    title=r.title,
                    short_title=r.short_title or None,
                    provider_user=r.provider_user_id,
                    contact_user=r.contact_user_id or None,
                    project_ids=project_ids,
                )
            )
        return ret

    @classmethod
    def get_bounding_geo(
        cls, session: Session, project_ids: ProjectIDListT
    ) -> Iterable[float]:
        # TODO: Why using the view?
        sql = (
            "SELECT min(o.latitude), max(o.latitude), min(o.longitude), max(o.longitude)"
            "  FROM objects o "
            " WHERE o.projid = ANY(:prj)"
        )
        res: Result = session.execute(text(sql), {"prj": project_ids})
        vals = res.first()
        assert vals
        return [a_val for a_val in vals]

    @classmethod
    def get_date_range(
        cls, session: Session, project_ids: ProjectIDListT
    ) -> Iterable[datetime]:
        # TODO: Why using the view?
        sql = (
            "SELECT min(o.objdate), max(o.objdate)"
            "  FROM objects o "
            " WHERE o.projid = ANY(:prj)"
        )
        res: Result = session.execute(text(sql), {"prj": project_ids})
        vals = res.first()
        assert vals
        return [a_val for a_val in vals]

    @staticmethod
    def do_after_load(session: Session, prj_id: int) -> None:
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
        # The EcoTaxa samples which are going to disappear.
        soon_deleted_samples: Query[Any] = Query(Sample.sampleid).filter(
            Sample.projid == prj_id
        )

        ret = []
        del_acquis_qry: Delete = Acquisition.__table__.delete().where(
            Acquisition.acq_sample_id.in_(soon_deleted_samples)
        )
        logger.info("Del acquisitions :%s", str(del_acquis_qry))
        gone_acqs = session.execute(del_acquis_qry).rowcount  # type:ignore  # case1
        ret.append(gone_acqs)
        logger.info("%d rows deleted", gone_acqs)

        del_sample_qry: Delete = Sample.__table__.delete().where(
            Sample.sampleid.in_(soon_deleted_samples)
        )
        logger.info("Del samples :%s", str(del_sample_qry))
        gone_sams = session.execute(del_sample_qry).rowcount  # type:ignore  # case1
        ret.append(gone_sams)
        logger.info("%d rows deleted", gone_sams)

        ret.append(gone_acqs)
        session.commit()
        return ret

    @staticmethod
    def delete(session: Session, prj_id: int) -> None:
        """
        Completely remove the project. It is assumed that contained objects have been removed.
        """
        # TODO: Remove from user preferences
        # Remove project
        session.query(Project).filter(Project.projid == prj_id).delete()
        # Remove privileges
        # TODO: Should be in a relationship rule already. To check using DB trace when moving to SQLAlchemy v2
        session.query(ProjectPrivilege).filter(
            ProjectPrivilege.projid == prj_id
        ).delete()

    @staticmethod
    def remap(
        session: Session, prj_id: int, table: MappedTableTypeT, remaps: List[RemapOp]
    ) -> None:
        """
        Apply remapping operations onto the given table for given project.
        """
        # Do the remapping, including blanking of unused columns
        values = {
            a_remap.to: text(a_remap.frm) if a_remap.frm is not None else a_remap.frm
            for a_remap in remaps
        }
        qry: Query[Any] = session.query(table)
        samples_4_prj: Query[Any]
        acqs_4_samples: Query[Any]
        if table == Sample:
            qry = qry.filter(Sample.projid == prj_id)
        elif table == Acquisition:
            samples_4_prj = Query(Sample.sampleid).filter(Sample.projid == prj_id)
            qry = qry.filter(Acquisition.acq_sample_id.in_(samples_4_prj))
        elif table == Process:
            samples_4_prj = Query(Sample.sampleid).filter(Sample.projid == prj_id)
            acqs_4_samples = Query(Acquisition.acquisid).filter(
                Acquisition.acq_sample_id.in_(samples_4_prj)
            )
            qry = qry.filter(Process.processid.in_(acqs_4_samples))
        elif table == ObjectFields:
            samples_4_prj = Query(Sample.sampleid).filter(Sample.projid == prj_id)
            acqs_4_samples = Query(Acquisition.acquisid).filter(
                Acquisition.acq_sample_id.in_(samples_4_prj)
            )
            objs_for_acqs: Query[Any] = Query(ObjectHeader.objid).filter(
                ObjectHeader.acquisid.in_(acqs_4_samples)
            )
            qry = qry.filter(ObjectFields.objfid.in_(objs_for_acqs))
        rowcount = qry.update(values=values, synchronize_session=False)

        logger.info("Remap query for %s: %s -> %d", table.__tablename__, qry, rowcount)

    @classmethod
    def get_all_object_ids(
        cls, session: Session, prj_id: int
    ) -> List[int]:  # TODO: Problem with recursive import -> ObjectIDListT:
        """
        Return the full list of objects IDs inside a project.
        TODO: Maybe better in ObjectBO
        """
        qry = session.query(ObjectHeader.objid)
        qry = qry.join(Acquisition, Acquisition.acquisid == ObjectHeader.acquisid)
        qry = qry.join(
            Sample,
            and_(Sample.sampleid == Acquisition.acq_sample_id, Sample.projid == prj_id),
        )
        return [an_id for an_id, in qry]

    @classmethod
    def incremental_update_taxo_stats(
        cls, session: Session, prj_id: int, collated_changes: ChangeTypeT
    ) -> None:
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
            pts_ins = (
                """INSERT INTO projects_taxo_stat(projid, id, nbr, nbr_v, nbr_d, nbr_p)
                                 SELECT :prj, COALESCE(obh.classif_id, -1), COUNT(*) nbr,
                                        COUNT(CASE WHEN obh.classif_qual = '"""
                + VALIDATED_CLASSIF_QUAL
                + """' THEN 1 END) nbr_v,
                                COUNT(CASE WHEN obh.classif_qual = '"""
                + DUBIOUS_CLASSIF_QUAL
                + """' THEN 1 END) nbr_d,
                                COUNT(CASE WHEN obh.classif_qual = '"""
                + PREDICTED_CLASSIF_QUAL
                + """' THEN 1 END) nbr_p
                           FROM %s obh
                           JOIN acquisitions acq ON acq.acquisid = obh.acquisid
                           JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = :prj
                          WHERE COALESCE(obh.classif_id, -1) = ANY(:ids)
                       GROUP BY obh.classif_id"""
                % ObjectHeader.__tablename__
            )
            session.execute(text(pts_ins), {"prj": prj_id, "ids": list(ids_not_in_db)})
        # Apply delta
        for classif_id, chg in collated_changes.items():
            if classif_id in ids_not_in_db:
                # The line was created just above, with OK values
                continue
            if ids_in_db[classif_id] + chg["n"] == 0:
                # The delta means 0 for this taxon in this project, delete the line
                sqlparam = {"prj": prj_id, "cid": classif_id}
                ts_sql = """DELETE FROM projects_taxo_stat
                             WHERE projid = :prj AND id = :cid"""
            else:
                # General case
                sqlparam = {
                    "prj": prj_id,
                    "cid": classif_id,
                    "nul": chg["n"],
                    "val": chg[VALIDATED_CLASSIF_QUAL],
                    "dub": chg[DUBIOUS_CLASSIF_QUAL],
                    "prd": chg[PREDICTED_CLASSIF_QUAL],
                }
                ts_sql = """UPDATE projects_taxo_stat
                               SET nbr=nbr+:nul, nbr_v=nbr_v+:val, nbr_d=nbr_d+:dub, nbr_p=nbr_p+:prd
                             WHERE projid = :prj AND id = :cid"""
            session.execute(text(ts_sql), sqlparam)

    @classmethod
    def get_sort_fields(cls, project: Project) -> OrderedDictT[str, str]:
        """
        Return the content of 'Fields available for sorting & Display In the manual classification page'
        """
        # e.g. area=area [pixel]
        #      meangreyobjet=mean [0-255]
        #      fractal_box=fractal
        ret: OrderedDictT[str, str] = OrderedDict()
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
    def get_sort_db_columns(
        cls, project: Project, mapping: Optional[TableMapping]
    ) -> List[str]:
        """
        Get sort list as DB columns, e.g. typically t03, n34
        """
        sort_list = cls.get_sort_fields(project)
        if mapping is None:
            return []
        mpg = mapping.find_tsv_cols(list(sort_list.keys()))
        return list(mpg.values())

    @classmethod
    def recompute_sunpos(cls, session: Session, prj_id: ProjectIDT) -> int:
        """
        Recompute sun position for all objects.
        :return the number of objects with sun position changed
        """
        used_fields = sorted(USED_FIELDS_FOR_SUNPOS)
        qry_cols = [ObjectHeader.objid, ObjectHeader.sunpos] + [
            getattr(ObjectHeader, fld) for fld in used_fields
        ]
        qry = session.query(*qry_cols)
        qry = qry.join(Acquisition, Acquisition.acquisid == ObjectHeader.acquisid)
        qry = qry.join(
            Sample,
            and_(Sample.sampleid == Acquisition.acq_sample_id, Sample.projid == prj_id),
        )
        ret = 0
        cache: Dict[typing.Tuple[Any], str] = {}
        for a_line in qry:
            objid, sunpos, *vals = a_line
            # A bit of caching
            vals = tuple(vals)
            if vals in cache:
                new_pos = cache[vals]
            else:
                vals_dict = {fld: val for fld, val in zip(used_fields, vals)}
                new_pos = compute_sun_position(Bean(vals_dict))
                cache[vals] = new_pos
            if new_pos != sunpos:
                obj = session.query(ObjectHeader).get(objid)
                assert obj is not None
                obj.sunpos = new_pos
                ret += 1
                if ret % 1000 == 0:
                    # Don't let a too big transaction grow
                    session.commit()
        session.commit()
        return ret


class ProjectBOSet(object):
    """
    Many projects...
    """

    def __init__(
        self,
        session: Session,
        prj_ids: ProjectIDListT,
        public: bool = False,
        fields: Optional[str] = FieldListType.default,
    ):
        # Query the project and ORM-load neighbours as well, as they will be needed in enrich()
        qry = select(Project)
        # qry = session.query(Project)
        qry = qry.options(
            subqueryload(Project.privs_for_members).joinedload(ProjectPrivilege.user)
            # Save a bit of time by joining privileges & users in a single query
            # Con: More data is returned as users in several projects are returned several times
        )
        qry = qry.options(joinedload(Project.variables))  # 1 -> 0,1
        qry = qry.options(joinedload(Project.instrument))  # 1 -> 0,1
        qry = qry.filter(Project.projid == any_(prj_ids))
        self.projects: List[ProjectBO] = []
        # De-duplicate
        projs = []
        with CodeTimer("%s BO projects query:" % len(prj_ids), logger):
            for (a_proj,) in session.execute(qry):
                projs.append(a_proj)
        # Build BOs and enrich
        with CodeTimer("%s BO projects init:" % len(projs), logger):
            self_projects_append = self.projects.append
            for a_proj in projs:
                if public:
                    self_projects_append(ProjectBO(a_proj).public_enrich())
                else:
                    self_projects_append(ProjectBO(a_proj).enrich())

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


class CollectionProjectBOSet(ProjectBOSet):
    """
    Operations on the collection projects .
    """

    def __init__(
        self,
        session: Session,
        prj_ids: ProjectIDListT,
        public: bool = False,
        fields: Optional[str] = FieldListType.default,
    ):
        super().__init__(session=session, prj_ids=prj_ids, public=public, fields=fields)

    def can_be_administered_by(self, session: Session, user_id: UserIDT):
        """We just expect an Exception thrown (or not)"""
        try:
            for project in self.projects:
                RightsBO.user_wants(
                    session,
                    user_id,
                    Action.ADMINISTRATE,
                    project.projid,
                    update_preference=False,
                )
            return True
        except AssertionError:
            return False


    def get_access_from_projects(self) -> Tuple[AccessLevelEnum, ProjectIDListT]:
        """
        return list of projects id validating the restricted_access.
        """
        noaccesses: ProjectIDListT = []
        restricted_access = max(
            [cast(AccessLevelEnum, project.access) for project in self.projects]
        )
        for project in self.projects:
            if project.access > restricted_access:
                noaccesses.append(project.projid)
        return restricted_access, noaccesses

    def get_annotators_from_histo(
        self, session, status: Optional[int] = None
    ) -> List[User]:
        project_ids: ProjectIDListT = [project.projid for project in self.projects]
        stats = ProjectBO.read_user_stats(session, project_ids)
        ids: UserIDListT = []
        for stat in stats:
            ids = ids + [annotator.id for annotator in stat.annotators]
        qry = session.query(
            User.id, User.email, User.name, User.orcid, User.organisation
        ).filter(User.id == any_(ids))
        if status is not None:
            qry = qry.filter(User.status == status)
        users: List[User] = []
        with CodeTimer("%s BO users query:" % len(ids), logger):
            for u in qry:
                # usr = ContactUserBO(
                #    u.id, u.email, u.name, u.orcid or "None", u.organisation
                # )
                users.append(u)

        return users

    def get_initclassiflist_from_projects(
        self,
    ) -> str:
        """
        Read aggregated Initial list of categories for these projects.
        """
        ret: List = []
        sep: str = ","
        for project in self.projects:
            initclassif = project.initclassiflist
            if initclassif is not None:
                ret = ret + initclassif.split(sep)
        ret = list(set(ret))
        return sep.join(ret)

    @staticmethod
    def _check_user_privilege(
        user: User, privlist: ContactUserListT
    ) -> ContactUserListT:
        if user.status == UserStatus.active.value:
            u: ContactUserBO = ContactUserBO(
                user.id,
                user.email,
                user.name,
                user.orcid or "None",
                user.organisation or "(Independent)",
            )
            if u not in privlist:
                privlist.append(u)
        return privlist

    def get_privileges_from_projects(
        self,
    ) -> Dict[str, ContactUserListT]:
        """
        Read aggregated Initial list of categories for these projects.
        """
        keys = {
            ProjectPrivilegeBO.VIEW: "viewers",
            ProjectPrivilegeBO.ANNOTATE: "annotators",
            ProjectPrivilegeBO.MANAGE: "managers",
        }
        projects = self.projects
        privileges: Dict[str, ContactUserListT] = {}
        # set common priv for users in all projects
        for key, value in keys.items():
            privileges[value] = list(
                set.intersection(
                    *[set(getattr(project, value)) for project in projects]
                )
            )
        # aggregate and remove anomalies from projects
        for u in privileges[keys[ProjectPrivilegeBO.VIEW]]:
            for k in [
                keys[ProjectPrivilegeBO.ANNOTATE],
                keys[ProjectPrivilegeBO.MANAGE],
            ]:
                if u in privileges[k]:
                    privileges[k].remove(u)
        for u in privileges[keys[ProjectPrivilegeBO.ANNOTATE]]:
            if u in privileges[keys[ProjectPrivilegeBO.MANAGE]]:
                privileges[keys[ProjectPrivilegeBO.MANAGE]].remove(u)
        return privileges

    def get_classiffieldlist_from_projects(
        self,
    ) -> str:
        """
        Read aggregated Fields available on sort & displayed field of Manual classif screen for these projects.
        """
        obj: Dict = {}
        ret: List = []
        linesep = "\n"
        projects = self.projects
        for project in projects:
            if project.classiffieldlist is None:
                fields = []
            else:
                fields = project.classiffieldlist.split(linesep)
            for field in fields:
                arrfield = field.split("=")
                key = arrfield[0].strip()
                if len(arrfield) == 2 and key != "" and key not in obj.keys():
                    # for same var name add only the first
                    obj[key] = arrfield[1].strip()
        for k, v in obj.items():
            ret.append(k + "=" + v)

        return linesep.join(ret)

    def get_mapping_from_projects(self) -> Dict[str, Dict[str, str]]:
        """
        Read common freecols for these projects. return List of common free cols names .
        """
        projects = [project._project for project in self.projects]
        mappings: ProjectSetMapping = ProjectSetMapping().load_from_projects(projects)
        dictmap = mappings.as_dict()
        return dictmap

    def get_common_from_projects(
        self,
        column: str,
    ) -> Tuple[Optional[str], ProjectIDListT]:
        """
        Read attribute for these projects. return None,projerr as soon as one project has a different one or value if all are equal.
        """
        values = [
            (project.projid, getattr(project, column, None))
            for project in self.projects
        ]
        commonvalue = None
        projerr: ProjectIDListT = []
        for i, value in enumerate(values):
            if i > 0 and value[1] != values[i - 1][1]:
                projerr.append(value[0])
        if len(projerr) == 0:
            commonvalue = values[0][1]
        return commonvalue, projerr
