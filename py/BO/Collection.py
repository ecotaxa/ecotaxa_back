# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Any, Optional, Set, cast

from BO.DataLicense import DataLicense, LicenseEnum
from BO.Project import ProjectIDListT
from DB import Collection, User, CollectionUserRole, Project
from DB import Session, Query
from DB.Collection import COLLECTION_ROLE_DATA_CREATOR, COLLECTION_ROLE_ASSOCIATED_PERSON, CollectionProject
from DB.helpers.Charset import to_latin1_compat
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

# Typings, to be clear that these are not e.g. proejct IDs
CollectionIDT = int
CollectionIDListT = List[int]


class CollectionBO(object):
    """
        A Collection business object, i.e. as seen from users.
    """

    def __init__(self, collection: Collection):
        self._collection = collection
        # Composing project IDs
        self.project_ids: ProjectIDListT = []
        # Involved members
        self.contact_user: Optional[User] = None
        self.creators: List[User] = []
        self.associates: List[User] = []

    def enrich(self):
        """
            Add some DB fields and relations as (hopefully more) meaningful attributes.
        """
        # Fetch contact user
        self.contact_user = None
        if self._collection.contact_user:
            self.contact_user = self._collection.contact_user
        # Reconstitute project list
        self._read_composing_projects()
        # Dispatch members by role
        by_role = {COLLECTION_ROLE_DATA_CREATOR: self.creators,
                   COLLECTION_ROLE_ASSOCIATED_PERSON: self.associates}
        a_user_and_role: CollectionUserRole
        # noinspection PyTypeChecker
        for a_user_and_role in self._collection.users_by_role:
            by_role[a_user_and_role.role].append(a_user_and_role.user)
        return self

    def _read_composing_projects(self):
        # noinspection PyTypeChecker
        self.project_ids = sorted([a_rec.projid for a_rec in self._collection.projects])

    def _add_composing_projects(self, session: Session, project_ids: ProjectIDListT):
        """
            Add the given projects into DB, doing sanity checks.
        """
        qry: Query = session.query(Project).filter(Project.projid.in_(project_ids))
        db_projects = qry.all()
        assert len(db_projects) == len(project_ids)
        prj_licenses: Set[LicenseEnum] = set()
        a_db_project: Project
        for a_db_project in db_projects:
            self._collection.projects.append(a_db_project)
            prj_licenses.add(cast(LicenseEnum, a_db_project.license))
        # Set self to most restrictive of all licenses
        max_restrict = max([DataLicense.RESTRICTION[a_prj_lic] for a_prj_lic in prj_licenses])
        self._collection.license = DataLicense.BY_RESTRICTION[max_restrict]

    def update(self, session: Session, title: str,
               project_ids: ProjectIDListT,
               contact_user: Any,
               citation: str, abstract: str, description: str,
               creators: List[Any], associates: List[Any]):
        project_ids.sort()
        assert project_ids == self.project_ids, "Cannot update composing projects yet"
        coll_id = self._collection.id
        # TODO: projects update using given list
        # TODO: license update using projects' ones
        # Simple fields update
        self._collection.title = to_latin1_compat(title)
        self._collection.citation = to_latin1_compat(citation)
        self._collection.abstract = to_latin1_compat(abstract)
        self._collection.description = to_latin1_compat(description)
        # Copy contact user id
        if contact_user is not None:
            self._collection.contact_user_id = contact_user.id
        # Dispatch members by role
        by_role = {COLLECTION_ROLE_DATA_CREATOR: creators,
                   COLLECTION_ROLE_ASSOCIATED_PERSON: associates}
        # Remove all to avoid diff-ing
        session.query(CollectionUserRole). \
            filter(CollectionUserRole.collection_id == coll_id).delete()
        # Add all
        for a_role, a_user_list in by_role.items():
            for a_user in a_user_list:
                session.add(CollectionUserRole(collection_id=coll_id,
                                               user_id=a_user.id,
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
        # Remove collection
        session.query(Collection). \
            filter(Collection.id == coll_id).delete()
        session.commit()
