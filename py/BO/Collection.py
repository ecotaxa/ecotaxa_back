# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Any, Optional

from BO.Project import ProjectIDT
from DB import Collection, User, CollectionUserRole
from DB import Session
from DB.Collection import COLLECTION_ROLE_DATA_CREATOR, COLLECTION_ROLE_ASSOCIATED_PERSON
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
        self.project_ids: List[ProjectIDT] = []
        # Involved members
        self.contact_user: Optional[User] = None
        self.creators: List[User] = []
        self.associates: List[User] = []

    def enrich(self):
        """
            Add DB fields and relations as (hopefully more) meaningful attributes
        """
        # Fetch contact user
        self.contact_user = self._collection.contact_user.all()[0]
        # Reconstitute project list
        # noinspection PyTypeChecker
        self.project_ids = [a_rec.project_id for a_rec in self._collection.projects]
        # Dispatch members by role
        by_role = {COLLECTION_ROLE_DATA_CREATOR: self.creators,
                   COLLECTION_ROLE_ASSOCIATED_PERSON: self.associates}
        a_user_and_role: CollectionUserRole
        # noinspection PyTypeChecker
        for a_user_and_role in self._collection.users:
            by_role[a_user_and_role.role].append(a_user_and_role.user)
        return self

    def update(self, session: Session, title: str,
               project_ids: List[int],
               contact_user: Any,
               citation: str, abstract: str, description: str,
               creators: List[Any], associates: List[Any]):
        coll_id = self._collection.id
        # TODO: projects update using given list
        # TODO: license update using projects' ones
        # Simple fields update
        self._collection.title = title
        self._collection.citation = citation
        self._collection.abstract = abstract
        self._collection.description = description
        # Copy contact user id
        self._collection.contact_user_id = contact_user.user_id
        # Dispatch members by role
        by_role = {COLLECTION_ROLE_DATA_CREATOR: creators,
                   COLLECTION_ROLE_ASSOCIATED_PERSON: associates}
        # Remove all to avoid tricky diffs
        session.query(CollectionUserRole). \
            filter(CollectionUserRole.collection_id == coll_id).delete()
        # Add all
        for a_role, a_user_list in by_role.items():
            for a_user in a_user_list:
                session.add(CollectionUserRole(collection_id=coll_id,
                                               user_id=a_user.id,
                                               role=a_role))
        session.commit()

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Collection field somehow then return it """
        return getattr(self._collection, item)

    @staticmethod
    def delete(session: Session, coll_id: CollectionIDT):
        """
            Completely remove the collection. 
            Being just a set of project references, the pointed-at projects are not impacted.
        """
        # Remove collection
        session.query(Collection). \
            filter(Collection.id == coll_id).delete()
        # That should be all as PG delete cascade does the job
        session.commit()

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
