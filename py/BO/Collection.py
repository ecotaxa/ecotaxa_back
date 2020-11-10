# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Any, Optional, Set, cast, Dict

from BO.DataLicense import DataLicense, LicenseEnum
from BO.Project import ProjectIDListT
from DB import Collection, User, CollectionUserRole, Project, Sample
from DB import Session, Query
from DB.Collection import COLLECTION_ROLE_DATA_CREATOR, COLLECTION_ROLE_ASSOCIATED_PERSON, CollectionProject, \
    CollectionOrgaRole
from DB.helpers.ORM import contains_eager
from helpers.DynamicLogs import get_logger

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

    def enrich(self):
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
        by_role_usr = {COLLECTION_ROLE_DATA_CREATOR: self.creator_users,
                       COLLECTION_ROLE_ASSOCIATED_PERSON: self.associate_users}
        a_user_and_role: CollectionUserRole
        # noinspection PyTypeChecker
        for a_user_and_role in self._collection.users_by_role:
            # noinspection PyTypeChecker
            by_role_usr[a_user_and_role.role].append(a_user_and_role.user)
        # Dispatch orgs by role
        by_role_org = {COLLECTION_ROLE_DATA_CREATOR: self.creator_organisations,
                       COLLECTION_ROLE_ASSOCIATED_PERSON: self.associate_organisations}
        an_org_and_role: CollectionOrgaRole
        # noinspection PyTypeChecker
        for an_org_and_role in self._collection.organisations_by_role:
            by_role_org[an_org_and_role.role].append(an_org_and_role.organisation)
        return self

    def _read_composing_projects(self):
        # noinspection PyTypeChecker
        self.project_ids = sorted([a_rec.projid for a_rec in self._collection.projects])

    def _add_composing_projects(self, session: Session, project_ids: ProjectIDListT):
        """
            Add the given projects into DB, doing sanity checks.
        """
        qry: Query = session.query(Project).filter(Project.projid.in_(project_ids))
        qry = qry.join(Sample, Project.all_samples).options(contains_eager(Project.all_samples))
        db_projects = qry.all()
        assert len(db_projects) == len(project_ids)
        # Loop on projects, adding them and collecting aggregated data
        prj_licenses: Set[LicenseEnum] = set()
        samples_per_project: Dict[str, str] = {}
        problems: List[str] = []
        a_db_project: Project
        for a_db_project in db_projects:
            self._collection.projects.append(a_db_project)
            prj_licenses.add(cast(LicenseEnum, a_db_project.license))
            # noinspection PyTypeChecker
            for a_sample in a_db_project.all_samples:
                sample_id = a_sample.orig_id
                # Sanity check: sample orig_id must be unique in the collection
                if sample_id in samples_per_project:
                    problems.append("Sample with orig_id %s is in both %s and %s" %
                                    (sample_id, samples_per_project[sample_id], a_db_project.title))
                else:
                    samples_per_project[sample_id] = a_db_project.title
        # Set self to most restrictive of all licenses
        max_restrict = max([DataLicense.RESTRICTION[a_prj_lic] for a_prj_lic in prj_licenses])
        self._collection.license = DataLicense.BY_RESTRICTION[max_restrict]
        # TODO: Default creators using classification history in DB. Knowing that it's partial.
        # Report (brutally) problems
        assert len(problems) == 0, "\n".join(problems)

    def update(self, session: Session, title: str,
               project_ids: ProjectIDListT,
               provider_user: Any, contact_user: Any,
               citation: str, abstract: str, description: str,
               creator_users: List[Any], associate_users: List[Any],
               creator_orgs: List[Any], associate_orgs: List[Any]
               ):
        project_ids.sort()
        # TODO: projects update using given list
        assert project_ids == self.project_ids, "Cannot update composing projects yet"
        coll_id = self._collection.id
        # Simple fields update
        self._collection.title = title
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
        by_role = {COLLECTION_ROLE_DATA_CREATOR: creator_users,
                   COLLECTION_ROLE_ASSOCIATED_PERSON: associate_users}
        # Remove all to avoid diff-ing
        session.query(CollectionUserRole). \
            filter(CollectionUserRole.collection_id == coll_id).delete()
        # Add all
        for a_role, a_user_list in by_role.items():
            for a_user in a_user_list:
                session.add(CollectionUserRole(collection_id=coll_id,
                                               user_id=a_user.id,
                                               role=a_role))
        # Dispatch orgs by role
        by_role_org = {COLLECTION_ROLE_DATA_CREATOR: creator_orgs,
                       COLLECTION_ROLE_ASSOCIATED_PERSON: associate_orgs}
        # Remove all to avoid diff-ing
        session.query(CollectionOrgaRole). \
            filter(CollectionOrgaRole.collection_id == coll_id).delete()
        # Add all
        for a_role, an_org_list in by_role_org.items():
            for an_org in an_org_list:
                session.add(CollectionOrgaRole(collection_id=coll_id,
                                               organisation=an_org,
                                               role=a_role))
        session.commit()

    def set_composing_projects(self, session: Session, project_ids: ProjectIDListT):
        """
            Core of the function: setting the composed projects.
        """
        # Read persisted side
        self._read_composing_projects()
        # Align with instructed list
        to_add = [a_prj_id for a_prj_id in project_ids
                  if a_prj_id not in self.project_ids]
        to_remove = [a_prj_id for a_prj_id in self.project_ids
                     if a_prj_id not in self.project_ids]
        assert len(to_remove) == 0, "No removal in collection composition yet"
        self._add_composing_projects(session, to_add)

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Collection field somehow then return it """
        return getattr(self._collection, item)

    @staticmethod
    def create(session: Session, title: str,
               project_ids: ProjectIDListT) -> CollectionIDT:
        """
            Create using minimum fields.
        """
        # Find the collection
        db_coll = Collection()
        db_coll.title = title
        session.add(db_coll)
        session.flush()  # to get the collection ID
        bo_coll = CollectionBO(db_coll)
        bo_coll.set_composing_projects(session, project_ids)
        session.commit()
        return bo_coll.id

    @staticmethod
    def get_one(session: Session, coll_id: CollectionIDT) -> Optional['CollectionBO']:
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
        session.query(CollectionProject). \
            filter(CollectionProject.collection_id == coll_id).delete()
        session.query(CollectionUserRole). \
            filter(CollectionUserRole.collection_id == coll_id).delete()
        session.query(CollectionOrgaRole). \
            filter(CollectionOrgaRole.collection_id == coll_id).delete()
        # Remove collection
        session.query(Collection). \
            filter(Collection.id == coll_id).delete()
        session.commit()
