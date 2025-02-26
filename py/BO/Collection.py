# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import re
import functools
from typing import List, Any, Optional, Set, cast, Dict, OrderedDict, Union
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
from DB.Organization import Organization
from BO.User import UserIDT, UserIDListT, ContactUserBO
from DB.helpers.ORM import contains_eager, func, any_
from helpers.DynamicLogs import get_logger
from helpers.FieldListType import FieldListType
from pydantic import BaseModel

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

    modif = ["title", "citation", "abstract", "description", "license"]
    no_modif = ["short_title", "external_id"]

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
        problems: List[str] = []
        a_db_project: Project
        for a_db_project in db_projects:
            self._collection.projects.append(a_db_project)

        # Report (brutally) problems
        assert len(problems) == 0, "\n".join(problems)

    @staticmethod
    def _get_annotators_from_histo(
        session, project_ids: ProjectIDListT, status: Optional[int] = None
    ) -> List[UserIDT]:
        pqry = session.query(User.id, User.organisation)
        pqry.join(User, User.id == ObjectHeader.classif_who)
        pqry.filter(Project.projid == any_(project_ids))
        pqry.filter(ObjectHeader.classif_who == User.id)
        if status is not None:
            pqry.filter(User.status == status)
        users: List[Any] = pqry.all()
        creator_user = [u.id for u in users]
        return creator_user

    def update(
        self,
        session: Session,
        collection_update: Dict[str, Any],
    ):
        by_role_schema = {
            "user": {
                "creator_users": COLLECTION_ROLE_DATA_CREATOR,
                "associate_users": COLLECTION_ROLE_ASSOCIATED_PERSON,
            },
            "org": {
                "creator_organisations": COLLECTION_ROLE_DATA_CREATOR,
                "associate_organisations": COLLECTION_ROLE_ASSOCIATED_PERSON,
            },
        }
        by_role: Dict[str, Any] = {}

        published = (
            self._collection.short_title != ""
            and self._collection.short_title is not None
        )
        for key, value in collection_update.items():
            if key == "project_ids":
                value.sort()
                # projects update using given list
                # Redo sanity check & aggregation as underlying projects might have changed (or not as stated just above. lol)
                self.set_composing_projects(session, value)
            # Simple fields update
            if key in self.modif:
                setattr(self._collection, key, value)
            elif key in self.no_modif:
                if not published or value not in ["", "?"]:
                    setattr(self._collection, key, value)
            elif key in ["provider_user", "contact_user"] and value is not None:
                # Copy provider user id contact user id
                setattr(self._collection, key + "_id", value["id"])
            for k, val in by_role_schema.items():
                if key in val.keys():
                    if k not in by_role:
                        by_role[k] = {}
                    v = val[key]
                    by_role[k][v] = value
        if len(by_role.keys()) > 0:
            self.add_collection_users(session, by_role)
        session.commit()

    def add_collection_users(
        self,
        session: Session,
        by_role: Dict[str, Dict[str, List[Any]]],
    ):
        coll_id = self._collection.id
        #  diff-ing
        if "user" in by_role:
            qry = session.query(CollectionUserRole).filter(
                CollectionUserRole.collection_id == coll_id
            )
            role_users = qry.all()
            qry.delete()
            # Add all
            for a_role, a_user_list in by_role["user"].items():

                for a_user in a_user_list:
                    session.add(
                        CollectionUserRole(
                            collection_id=coll_id, user_id=a_user["id"], role=a_role
                        )
                    )

        # Dispatch orgs by role
        if "org" in by_role:
            # Remove all to avoid diff-ing
            qry = session.query(CollectionOrgaRole).filter(
                CollectionOrgaRole.collection_id == coll_id
            )
            role_org = qry.all()
            qry.delete()
            # Add all
            for a_role, an_org_list in by_role["org"].items():
                for an_org in an_org_list:
                    an_org = an_org.strip()
                    session.add(
                        CollectionOrgaRole(
                            collection_id=coll_id, organisation=an_org, role=a_role
                        )
                    )
            if (
                COLLECTION_ROLE_DATA_CREATOR in by_role["org"]
                and len(by_role["org"][COLLECTION_ROLE_DATA_CREATOR]) > 0
            ):
                # First org is the institutionCode provider
                inst_code_provider = by_role["org"][COLLECTION_ROLE_DATA_CREATOR][0]
                inst_code_provider = inst_code_provider.strip()
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
        if len(to_remove) > 0:
            session.query(CollectionProject).filter(
                CollectionProject.project_id.in_(to_remove)
            ).delete()
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
    def delete(session: Session, coll_id: CollectionIDT) -> bool:
        """
        Completely remove the collection.
        Being just a set of project references, the pointed-at projects are not impacted.
        """
        # check if collection is published
        published = (
            session.query(Collection.short_title != None)
            .filter(Collection.short_title != "")
            .filter(Collection.id == coll_id)
            .scalar()
        )
        if published is not None:
            return False
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
        return True

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


class MinimalCollectionBO(BaseModel):
    id: CollectionIDT
    external_id: Union[str, None] = None
    title: str
    short_title: Union[str, None] = None
    provider_user: UserIDT
    contact_user: Union[UserIDT, None] = None
    project_ids: ProjectIDListT
