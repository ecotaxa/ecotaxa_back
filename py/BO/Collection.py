# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import re
from typing import List, Any, Optional, Set, Dict, Union
from BO.DataLicense import LicenseEnum
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
from DB.User import User, Person, Organization, OrganizationIDT
from DB.ProjectPrivilege import ProjectPrivilege
from BO.User import UserIDT, GuestIDT, PersonBO
from BO.ProjectPrivilege import ProjectPrivilegeBO
from DB.helpers.ORM import contains_eager, func, any_
from helpers.DynamicLogs import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)

# Typings, to be clear that these are not e.g. project IDs
CollectionIDT = int
CollectionIDListT = List[int]

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
creators_key = "creators"
associates_key = "associates"
user_order_type = "u"
org_order_type = "o"
class CollectionBO(object):
    """
    A Collection business object, i.e. as seen from users.
    """

    modif = ["title", "citation", "abstract", "description", "license", "external_id"]
    no_modif = ["short_title"]

    def __init__(self, collection: Collection):
        self._collection: Collection = collection
        # Composing project IDs
        self.project_ids: ProjectIDListT = []
        # Involved members
        self.provider_user: Optional[User] = None
        self.contact_user: Optional[User] = None
        self.creator_users: List[User] = []
        self.associate_users: List[User] = []
        self.creator_organisations: List[Organization] = []
        self.associate_organisations: List[Organization] = []
        self.code_provider_org: Optional[str] = None
        self.display_order: Dict[str,Any] = {creators_key:[],associates_key:[]}

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
        self._get_by_role()
        return self

    def _read_composing_projects(self):
        self.project_ids = sorted([a_rec.projid for a_rec in self._collection.projects])

    def _add_composing_projects(
        self,
        session: Session,
        project_ids: ProjectIDListT,
    ) -> Optional[str]:
        """
        Add the given projects into DB, doing sanity checks.
        """
        qry = session.query(Project).filter(Project.projid.in_(project_ids))
        qry = qry.join(Sample, Project.all_samples).options(
            contains_eager(Project.all_samples)
        )
        db_projects = qry.all()
        problems: List[str] = []
        if len(db_projects) != len(project_ids):
            problems.append(
                "One or more projects has no sample and can't be added to the collection."
            )
        # Loop on projects, adding them and collecting aggregated data
        else:
            a_db_project: Project
            for a_db_project in db_projects:
                self._collection.projects.append(a_db_project)

        if len(problems):
            return "\n".join(problems)
        return None

    def _get_by_role(self)->Dict[str,Any]:
        # Order members by role
        by_role_usr:Dict[str,Any] = { COLLECTION_ROLE_DATA_CREATOR: self.creator_users,
            COLLECTION_ROLE_ASSOCIATED_PERSON: self.associate_users,
        }

        display_order: Dict[str,Any]= {creators_key:[],associates_key:[]}
        display_order_creator: Dict[str,Any] = {}
        display_order_associated: Dict[str,Any] = {}
        ord_creator: Dict[str,Any] = {}
        ord_assoc: Dict[str,Any] = {}
        a_user_and_role: CollectionUserRole
        for a_user_and_role in self._collection.users_by_role:

            if a_user_and_role.display_order is None:
                o = 0
            else:
                o = a_user_and_role.display_order
            if str(o) not in ord_creator.keys():
                ord_creator[str(o)] = []
            if str(o) not in ord_assoc.keys():
                ord_assoc[str(o)] = []
            if a_user_and_role.user is not None:
                by_role_usr[a_user_and_role.role].append(a_user_and_role.user)
                if a_user_and_role.role==COLLECTION_ROLE_DATA_CREATOR:
                    ord_creator[str(o)].append(str(a_user_and_role.user.id)+"_"+user_order_type)
                else:
                    ord_assoc[str(o)].append(str(a_user_and_role.user.id)+"_"+user_order_type)
            else:
                by_role_usr[a_user_and_role.role].append(a_user_and_role.guest)
                if a_user_and_role.role==COLLECTION_ROLE_DATA_CREATOR:
                    ord_creator[str(o)].append(str(a_user_and_role.guest.id)+"_"+user_order_type)
                elif a_user_and_role==COLLECTION_ROLE_ASSOCIATED_PERSON:
                    ord_assoc[str(o)].append(str(a_user_and_role.guest.id)+"_"+user_order_type)

        display_order_creator.update(ord_creator)
        display_order_associated.update(ord_assoc)
        # Dispatch orgs by role
        by_role_org = {
            COLLECTION_ROLE_DATA_CREATOR: self.creator_organisations,
            COLLECTION_ROLE_ASSOCIATED_PERSON: self.associate_organisations,
        }
        an_org_and_role: CollectionOrgaRole
        provider = COLLECTION_ROLE_INSTITUTION_CODE_PROVIDER
        for an_org_and_role in self._collection.organisations_by_role:
            if an_org_and_role.display_order is None:
                o = 0
            else:
                o = an_org_and_role.display_order
            if str(o) not in ord_creator.keys():
                ord_creator[str(o)]=[]
            if str(o) not in ord_assoc.keys():
                ord_assoc[str(o)]=[]
            if an_org_and_role.role==COLLECTION_ROLE_DATA_CREATOR:
                ord_creator[str(o)].append(str(an_org_and_role.organization.id)+"_"+org_order_type)
            elif an_org_and_role.role==COLLECTION_ROLE_ASSOCIATED_PERSON:
                ord_assoc[str(o)].append(str(an_org_and_role.organization.id)+"_"+org_order_type)
            if an_org_and_role.role == provider:
                self.code_provider_org = an_org_and_role.organization.name
            else:
                by_role_org[an_org_and_role.role].append(an_org_and_role.organization)

        display_order_creator.update(ord_creator)
        display_order_associated.update(ord_assoc)
        by_role:Dict[str,Any] = {"user":by_role_usr, "org":by_role_org}
        for k, c in sorted(display_order_creator.items(), key=lambda creator: int(creator[0]) ):
            display_order[creators_key].extend(list(set(c)))
        for k, v in sorted(display_order_associated.items(), key=lambda associate: int(associate[0])):
            display_order[associates_key].extend(list(set(v)))
        self.display_order=display_order
        return by_role

    @staticmethod
    def _get_annotators_from_histo(
        session, project_ids: ProjectIDListT, status: Optional[int] = None
    ) -> List[UserIDT]:
        pqry = session.query(User)
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
    ) -> Optional[str]:
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
                res = self.set_composing_projects(session, value)
                # return problems - will be catched by service
                if res is not None:
                    return res
            # Simple fields update
            display_order:Dict[str,Any]= {creators_key: [],associates_key: []}
            if key in self.modif:
                setattr(self._collection, key, value)
            elif key in self.no_modif:
                # short_title cannot be modified
                if not published:
                    setattr(self._collection, key, value)
            elif key in ["provider_user", "contact_user"] and value is not None:
                # Copy provider user id contact user id
                id_user = self.get_user_id(session, value)
                setattr(self._collection, key + "_id", id_user)
            else:
                for k, val in by_role_schema.items():
                    if key in val.keys():
                        if k not in by_role:
                            by_role[k] = {}
                        v = val[key]
                        by_role[k][v] = value
        if len(by_role["user"]) > 0 or len(by_role["org"]) > 0:
            self.display_order = collection_update["display_order"]
            self.add_collection_users(session, by_role)
        session.commit()
        return None

    def add_collection_users(
        self,
        session: Session,
        by_role: Dict[str, Dict[str, List[Any]]],
    ):
        coll_id = self._collection.id
        #  diff-ing
        roles= {COLLECTION_ROLE_DATA_CREATOR : creators_key, COLLECTION_ROLE_ASSOCIATED_PERSON : associates_key}
        if "user" in by_role:
            _ = (
                session.query(CollectionUserRole)
                .filter(CollectionUserRole.collection_id == coll_id)
                .delete()
            )
            # Add all
            for a_role, a_user_list in by_role["user"].items():
                for a_user in a_user_list:
                    user_id = CollectionBO.get_user_id(session, a_user)
                    collurole = CollectionUserRole()
                    collurole.collection_id = coll_id
                    collurole.user_id = user_id
                    collurole.role = a_role
                    collurole.display_order = self.display_order[roles[a_role]].index(str(user_id)+"_"+user_order_type)
                    session.add(collurole)


        # Dispatch orgs by role
        if "org" in by_role:
            # Remove all to avoid diff-ing
            _ = (
                session.query(CollectionOrgaRole)
                .filter(CollectionOrgaRole.collection_id == coll_id)
                .delete()
            )
            # Add all
            inst_code_provider = 0
            for a_role, an_org_list in by_role["org"].items():
                for an_org in an_org_list:
                    org_id = CollectionBO.get_organisation_id(session, an_org)
                    collorole = CollectionOrgaRole()
                    collorole.collection_id = coll_id
                    collorole.organization_id = org_id
                    collorole.role = a_role
                    collorole.display_order = self.display_order[roles[a_role]].index(str(org_id)+"_"+org_order_type)
                    session.add(collorole)
                    # First org is the institutionCode provider
                    if (
                        a_role == COLLECTION_ROLE_DATA_CREATOR
                        and inst_code_provider == 0
                        and org_id is not None
                    ):
                        inst_code_provider = org_id
            if inst_code_provider > 0:
                collorole = CollectionOrgaRole()
                collorole.collection_id = coll_id
                collorole.organization_id = inst_code_provider
                collorole.role = COLLECTION_ROLE_INSTITUTION_CODE_PROVIDER
                session.add(collorole)

    def set_composing_projects(
        self, session: Session, project_ids: ProjectIDListT
    ) -> Optional[str]:
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
            a_prj_id for a_prj_id in self.project_ids if a_prj_id not in project_ids
        ]
        if len(to_remove) > 0:
            session.query(CollectionProject).filter(
                CollectionProject.project_id.in_(to_remove)
            ).delete()
        if len(to_add):
            res = self._add_composing_projects(session, to_add)
            return res
        elif len(self.project_ids) == 0:
            return "No project in the collection"
        return None

    @staticmethod
    def get_user_id(session: Session, a_user: Union[int, str, Dict]) -> Optional[int]:
        if isinstance(a_user, int):
            return a_user
        if isinstance(a_user, str):
            if "@" in a_user:
                user_id = (
                    session.query(Person.id).filter(Person.email.ilike(a_user)).scalar()
                )
            else:
                user_id = (
                    session.query(Person.id).filter(Person.name.ilike(a_user)).scalar()
                )

            return user_id
        return a_user["id"]

    @staticmethod
    def get_organisation_id(
        session: Session, a_org: Union[int, str, Dict]
    ) -> Optional[int]:
        if isinstance(a_org, int):
            return a_org
        if isinstance(a_org, str):
            org_id = PersonBO.get_organization_id(session, a_org)
            return org_id
        return a_org["id"]

    def __getattr__(self, item):
        """Fallback for 'not found' field after the C getattr() call.
        If we did not enrich a Collection field somehow then return it"""
        return getattr(self._collection, item)

    @staticmethod
    def create(
        session: Session, title: str, project_ids: ProjectIDListT
    ) -> Union[CollectionIDT, str]:
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
        res = bo_coll._add_composing_projects(session, project_ids)
        if res is None:
            session.commit()
            return bo_coll.id
        else:
            return res

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
        # TODO ugly filter
        published = (
            session.query(Collection.external_id)
            .filter(Collection.external_id is not None)
            .filter(Collection.external_id != "")
            .filter(Collection.external_id != "?")
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

    @staticmethod
    def is_a_manager(session: Session, user: User) -> CollectionIDListT:
        """
        check if current_user can admin guest or organization
        """
        if not user.is_manager():
            collection_ids = CollectionBO.projects_managed_by(session, user)
            return collection_ids
        return []

    @staticmethod
    def projects_managed_by(session: Session, user: User) -> CollectionIDListT:
        """
        common managers of a collection
        """
        qry = (
            session.query(CollectionProject.collection_id)
            .join(
                ProjectPrivilege,
                CollectionProject.project_id == ProjectPrivilege.projid,
            )
            .filter(ProjectPrivilege.member == user.id)
            .filter(ProjectPrivilege.privilege == ProjectPrivilegeBO.MANAGE)
            .group_by(CollectionProject.collection_id)
        )
        collection_ids = []
        for collection_id in qry:
            collection_ids.append(collection_id[0])
        return collection_ids

    @staticmethod
    def can_manage_guest(session: Session, user: User, guest_id: GuestIDT) -> bool:
        """
        check if user can update guest profile (has to be creator_users or associates_users  in a collection managed by the user)
        """
        if user.is_manager():
            return True
        collection_ids = CollectionBO.is_a_manager(session, user)
        qry = (
            session.query(CollectionUserRole.collection_id)
            .filter(CollectionUserRole.collection_id.in_(collection_ids))
            .filter(CollectionUserRole.user_id == guest_id)
        )
        can_manage = qry.scalar()
        return can_manage is not None

    @staticmethod
    def can_manage_organization(
        session: Session, user: User, organization: OrganizationIDT
    ) -> bool:
        """
        check if user can update organization name or directories (has to be creator_organisations or associates_organisations  in a collection managed by the user)
        """
        if user.is_manager():
            return True
        collection_ids = CollectionBO.is_a_manager(session, user)
        qry = (
            session.query(CollectionOrgaRole.collection_id)
            .filter(CollectionOrgaRole.collection_id.in_(collection_ids))
            .filter(CollectionOrgaRole.organisation == organization)
        )
        can_manage = qry.scalar()
        return can_manage is not None

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