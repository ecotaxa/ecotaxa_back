# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import re
import functools
from typing import List, Any, Optional, Set, cast, Dict, OrderedDict
from dataclasses import dataclass
from BO.DataLicense import DataLicense, LicenseEnum
from BO.Sample import SampleOrigIDT
from DB import Session
from DB.Collection import (
    COLLECTION_ROLE_DATA_CREATOR,
    COLLECTION_ROLE_ASSOCIATED_PERSON,
    CollectionProject,
    CollectionOrgaRole,
    Collection,
    CollectionUserRole,
    COLLECTION_ROLE_INSTITUTION_CODE_PROVIDER,
)
from DB.Project import ProjectIDListT, Project
from DB.Object import ObjectHeader
from DB.Sample import Sample
from DB.User import User
from BO.User import UserIDT, UserIDListT, ContactUserBO
from DB.helpers.ORM import contains_eager, func, any_
from helpers.DynamicLogs import get_logger
from helpers.FieldListType import FieldListType

logger = get_logger(__name__)

# Typings, to be clear that these are not e.g. project IDs
CollectionIDT = int
CollectionIDListT = List[int]

# Temporary until a proper entity appears
OrganisationIDT = str


class CollectionBO(object):
    """
    A Collection business object, i.e. as seen from users.
    """

    def __init__(self, collection: Collection):
        self._collection: Collection = collection
        # Composing project IDs
        self.project_ids: ProjectIDListT = []
        # Involved members
        self.provider_user: Optional[User] = None
        self.contact_user: Optional[User] = None
        self.creator_users: List[User] = []
        self.associate_users: List[User] = []
        self.creator_organisations: List[OrganisationIDT] = []
        self.associate_organisations: List[OrganisationIDT] = []
        self.code_provider_org: Optional[OrganisationIDT] = None

    def enrich(self) -> "CollectionBO":
        """
        Add some DB fields and relations as (hopefully more) meaningful attributes.
        """
        # Fetch provider user
        self.provider_user = None
        if self._collection.provider_user:
            self.provider_user = self._collection.provider_user
        # Fetch contact user
        self.contact_user = None
        if self._collection.contact_user:
            self.contact_user = self._collection.contact_user
        # Reconstitute project list
        self._read_composing_projects()
        # Dispatch members by role
        by_role_usr = {
            COLLECTION_ROLE_DATA_CREATOR: self.creator_users,
            COLLECTION_ROLE_ASSOCIATED_PERSON: self.associate_users,
        }
        a_user_and_role: CollectionUserRole
        for a_user_and_role in self._collection.users_by_role:
            by_role_usr[a_user_and_role.role].append(a_user_and_role.user)
        # Dispatch orgs by role
        by_role_org = {
            COLLECTION_ROLE_DATA_CREATOR: self.creator_organisations,
            COLLECTION_ROLE_ASSOCIATED_PERSON: self.associate_organisations,
        }
        an_org_and_role: CollectionOrgaRole
        provider = COLLECTION_ROLE_INSTITUTION_CODE_PROVIDER
        for an_org_and_role in self._collection.organisations_by_role:
            if an_org_and_role.role == provider:
                self.code_provider_org = an_org_and_role.organisation
            else:
                by_role_org[an_org_and_role.role].append(an_org_and_role.organisation)
        return self

    def _read_composing_projects(self):
        self.project_ids = sorted([a_rec.projid for a_rec in self._collection.projects])

    def _add_composing_projects(
        self,
        session: Session,
        project_ids: ProjectIDListT,
    ):
        """
        Add the given projects into DB, doing sanity checks.
        """
        qry = session.query(Project).filter(Project.projid.in_(project_ids))
        qry = qry.join(Sample, Project.all_samples).options(
            contains_eager(Project.all_samples)
        )
        db_projects = qry.all()
        assert len(db_projects) == len(project_ids)
        # Loop on projects, adding them and collecting aggregated data
        prj_licenses: Set[LicenseEnum] = set()
        problems: List[str] = []
        a_db_project: Project
        for a_db_project in db_projects:
            self._collection.projects.append(a_db_project)

        # TODO: Default creators using classification history in DB. Knowing that it's partial.

        creator_user, creator_org = self._get_annotators_from_histo(
            session, project_ids
        )
        by_role_user = {
            COLLECTION_ROLE_DATA_CREATOR: creator_user,
        }
        # Dispatch orgs by role
        by_role_org = {
            COLLECTION_ROLE_DATA_CREATOR: creator_org,
        }
        self._add_collection_users(session, self.id, by_role_user, by_role_org)
        # Report (brutally) problems
        assert len(problems) == 0, "\n".join(problems)

    # static methods  get aggregated data from projects
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

    @staticmethod
    def _get_annotators_from_histo(
        session, project_ids: ProjectIDListT, status: Optional[int] = None
    ) -> List[User]:
        pqry = session.query(User.id, User.organisation)
        pqry.join(User, User.id == ObjectHeader.classif_who)
        pqry.filter(Project.projid == any_(project_ids))
        pqry.filter(ObjectHeader.classif_who == User.id)
        if status is not None:
            pqry.filter(User.status == status)
        users: List[Any] = pqry.all()
        creator_user = [u.id for u in users]
        creator_org = [u.organisation for u in users]
        return creator_user, creator_org

    def update(
        self,
        session: Session,
        title: str,
        short_title: Optional[str],
        project_ids: ProjectIDListT,
        provider_user: Any,
        contact_user: Any,
        citation: Optional[str],
        abstract: Optional[str],
        description: Optional[str],
        creator_users: List[Any],
        associate_users: List[Any],
        creator_orgs: List[Any],
        associate_orgs: List[Any],
    ):
        project_ids.sort()
        # TODO: projects update using given list
        assert project_ids == self.project_ids, "Cannot update composing projects yet"
        # Redo sanity check & aggregation as underlying projects might have changed (or not as stated just above. lol)
        self.set_composing_projects(session, project_ids)
        coll_id = self._collection.id
        # Simple fields update
        self._collection.title = title
        self._collection.short_title = short_title
        self._collection.citation = citation
        self._collection.abstract = abstract
        self._collection.description = description
        # Copy provider user id
        if provider_user is not None:
            self._collection.provider_user_id = provider_user.id
        # Copy contact user id
        if contact_user is not None:
            self._collection.contact_user_id = contact_user.id

        # Dispatch members by role
        by_role_user = {
            COLLECTION_ROLE_DATA_CREATOR: creator_users,
            COLLECTION_ROLE_ASSOCIATED_PERSON: associate_users,
        }
        # Dispatch orgs by role
        by_role_org = {
            COLLECTION_ROLE_DATA_CREATOR: creator_orgs,
            COLLECTION_ROLE_ASSOCIATED_PERSON: associate_orgs,
        }
        self._add_collection_users(session, coll_id, by_role_user, by_role_org)
        session.commit()

    def _add_collection_users(
        self,
        session: Session,
        coll_id: int,
        by_role_user: Dict[str, List[Any]],
        by_role_org: Dict[str, List[Any]],
    ):
        """Dispatch members and org by role"""

        #  diff-ing
        qry = session.query(CollectionUserRole).filter(
            CollectionUserRole.collection_id == coll_id
        )
        role_users = qry.all()
        print("________role_user", role_users)
        qry.delete()
        # Add all
        for a_role, a_user_list in by_role_user.items():
            for a_user in a_user_list:
                session.add(
                    CollectionUserRole(
                        collection_id=coll_id, user_id=a_user.id, role=a_role
                    )
                )

        # Dispatch orgs by role
        # Remove all to avoid diff-ing
        qry = session.query(CollectionOrgaRole).filter(
            CollectionOrgaRole.collection_id == coll_id
        )
        role_org = qry.all()
        print("________role_org", role_org)
        qry.delete()
        # Add all
        for a_role, an_org_list in by_role_org.items():
            for an_org in an_org_list:
                session.add(
                    CollectionOrgaRole(
                        collection_id=coll_id, organisation=an_org, role=a_role
                    )
                )
        # First org is the institutionCode provider
        inst_code_provider = by_role_org[COLLECTION_ROLE_DATA_CREATOR][0]
        session.add(
            CollectionOrgaRole(
                collection_id=coll_id,
                organisation=inst_code_provider,
                role=COLLECTION_ROLE_INSTITUTION_CODE_PROVIDER,
            )
        )

    def set_composing_projects(self, session: Session, project_ids: ProjectIDListT):
        """
        Core of the function: setting the composed projects.
        """
        # Read persisted side
        self._read_composing_projects()
        # Align with instructed list
        to_add = [
            a_prj_id for a_prj_id in project_ids if a_prj_id not in self.project_ids
        ]
        to_remove = [
            a_prj_id
            for a_prj_id in self.project_ids
            if a_prj_id not in self.project_ids
        ]
        assert len(to_remove) == 0, "No removal in collection composition yet"
        if len(to_add):
            self._add_composing_projects(session, to_add)

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a Collection field somehow then return it"""
        return getattr(self._collection, item)

    @staticmethod
    def create(
        session: Session, title: str, project_ids: ProjectIDListT
    ) -> CollectionIDT:
        """
        Create using minimum fields.
        """
        # Create the collection
        db_coll = Collection()
        db_coll.title = title
        db_coll.external_id = "?"
        db_coll.external_id_system = "?"
        db_coll.license = LicenseEnum.NO_LICENSE.value
        session.add(db_coll)
        session.flush()  # to get the collection ID
        bo_coll = CollectionBO(db_coll)
        bo_coll._add_composing_projects(session, project_ids)
        session.commit()
        return bo_coll.id

    @staticmethod
    def get_one(session: Session, coll_id: CollectionIDT) -> Optional["CollectionBO"]:
        """
        Find a Collection by its ID and return it, None if not found.
        """
        # Find the collection
        ret = session.query(Collection).get(coll_id)
        if ret is None:
            return None
        else:
            return CollectionBO(ret).enrich()

    @staticmethod
    def delete(session: Session, coll_id: CollectionIDT):
        """
        Completely remove the collection.
        Being just a set of project references, the pointed-at projects are not impacted.
        """
        # Remove links first
        session.query(CollectionProject).filter(
            CollectionProject.collection_id == coll_id
        ).delete()
        session.query(CollectionUserRole).filter(
            CollectionUserRole.collection_id == coll_id
        ).delete()
        session.query(CollectionOrgaRole).filter(
            CollectionOrgaRole.collection_id == coll_id
        ).delete()
        # Remove collection
        session.query(Collection).filter(Collection.id == coll_id).delete()
        session.commit()

    CODE_RE = re.compile(
        "\\(([A-Z]+)\\)$"
    )  # Quite strict, just uppercase letters at the end of the name

    def get_institution_code(self) -> str:
        """
        Conventionally, institution code is the first (sent via API) creator org short name.
        e.g. Institut de la Mer de Villefranche (IMEV) -> IMEV
        """
        found = self.CODE_RE.findall(str(self.code_provider_org))
        if len(found) == 1:
            return found[0]
        else:
            return "?"

    def homonym_samples(self, ro_session: Session) -> Set[SampleOrigIDT]:
        """
        Return the samples with exact same orig_id name, but in different projects.
        """
        qry = ro_session.query(Sample.orig_id)
        qry = qry.filter(Sample.projid == any_(self.project_ids))
        qry = qry.group_by(Sample.orig_id)
        qry = qry.having(func.count(Sample.orig_id) > 1)
        return set([an_id for an_id, in qry])


@dataclass()
class MinimalCollectionBO:
    id: CollectionIDT
    external_id: str
    title: str
    short_title: str
    provider_user_id: UserIDT
    contact_user: Optional[ContactUserBO]
    project_ids: ProjectIDListT
