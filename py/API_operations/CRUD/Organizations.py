# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2025  Picheral, Colin, Irisson (UPMC-CNRS)
#

from typing import Optional, List

from fastapi import HTTPException

from API_models.crud import OrganizationModel
from BO.Collection import CollectionBO, CollectionIDListT
from BO.Rights import RightsBO, NOT_AUTHORIZED, NOT_FOUND
from DB.Collection import CollectionUserRole
from DB.User import (
    Organization,
    OrganizationIDListT,
    OrganizationIDT,
    PeopleOrganizationDirectory,
    User,
    UserIDT,
)
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_ALREADY_EXISTS,
    DETAIL_CANT_CHECK_VALIDITY,
)
from providers.EDMO import EDMOFetcher, EDMOOrganization
from ..helpers.Service import Service
from ..helpers.UserValidation import ActivationType
from .Users import UserService

logger = get_logger(__name__)

# Organization directories are comma-separated "<directory>:<code>", e.g. "edmo:1278"
DIRECTORIES_SEP = ","
EDMO_PREFIX = PeopleOrganizationDirectory.edmo.name + ":"


def edmo_code_from_directories(directories: Optional[str]) -> Optional[int]:
    """The EDMO code in directories, if any"""
    for an_entry in (directories or "").split(DIRECTORIES_SEP):
        an_entry = an_entry.strip()
        if an_entry.startswith(EDMO_PREFIX) and an_entry[len(EDMO_PREFIX) :].isdigit():
            return int(an_entry[len(EDMO_PREFIX) :])
    return None


def directories_with_edmo(directories: Optional[str], code: int) -> str:
    """Directories with the EDMO reference replaced or added, other ones kept"""
    entries = [
        an_entry.strip()
        for an_entry in (directories or "").split(DIRECTORIES_SEP)
        if an_entry.strip() and not an_entry.strip().startswith(EDMO_PREFIX)
    ]
    return DIRECTORIES_SEP.join([EDMO_PREFIX + str(code)] + entries)


class OrganizationService(Service):
    """
    Basic CRUD API_operations on Guest
    """

    UPDATABLE_COLS = [
        Organization.name,
        Organization.directories,
    ]

    # check context to know if the email has to be verified

    def create_organization(
        self,
        current_user_id: Optional[UserIDT],
        new_org: OrganizationModel,
        token: Optional[str] = None,
    ) -> OrganizationIDT:
        # Must be a valid user, e.g. choosing one's organization in one's profile, or creating an account
        if current_user_id is not None:
            RightsBO.get_user_throw(self.ro_session, current_user_id)
        else:
            self._is_registering_throw(token)
        # official name & code from EDMO, when found there
        new_org = self._with_edmo(new_org)
        # check valid org
        self._is_valid_org_throw(new_org, new_org.id)
        organization = Organization()
        self.session.add(organization)
        cols_to_upd = self.UPDATABLE_COLS
        self._set_organization_row(
            new_org,
            organization,
            cols_to_upd=cols_to_upd,
        )
        return organization.id

    def update_organization(
        self,
        current_user_id: UserIDT,
        organization: OrganizationIDT,
        update_src: OrganizationModel,
    ) -> None:
        """
        Update an organization, who can be any organization of one of my collections if I'm an app manager.
        """
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        self._can_manage_organization_throw(current_user, organization)
        org_to_update: Optional[Organization] = self.session.get(
            Organization, organization
        )
        if org_to_update is None:
            raise HTTPException(status_code=422, detail=[NOT_FOUND])
        self._is_valid_org_throw(update_src, org_to_update.id)
        cols_to_upd = self.UPDATABLE_COLS
        self._set_organization_row(
            update_src,
            org_to_update,
            cols_to_upd=cols_to_upd,
        )

    @staticmethod
    def _with_edmo(new_org: OrganizationModel) -> OrganizationModel:
        """
        Look the organization up in EDMO: by its code if an EDMO reference is in its directories,
        else by its name. When found, use the official name and set the EDMO reference.
        If not found or EDMO is not reachable, the organization is left as is.
        """
        code = edmo_code_from_directories(new_org.directories)
        if code is not None:
            found = EDMOFetcher.get_by_code(code)
        else:
            by_name = EDMOFetcher.find_by_name(new_org.name)
            # Ambiguous names are left to the user
            found = by_name[0] if len(by_name) == 1 else None
        if found is None:
            return new_org
        logger.info(
            "Organization '%s' found in EDMO: %d '%s'",
            new_org.name,
            found.code,
            found.name,
        )
        return new_org.model_copy(
            update={
                "name": found.name,
                "directories": directories_with_edmo(new_org.directories, found.code),
            }
        )

    def _limit_qry(self, current_user: User, qry):
        if not current_user.is_manager():
            collection_ids = CollectionBO.projects_managed_by(
                self.ro_session, current_user
            )
            qry = qry.join(CollectionUserRole.collection).filter(
                CollectionUserRole.collection_id.in_(collection_ids)
            )
        return qry

    def search(self, by_name: Optional[str]) -> List[Organization]:
        qry = self.ro_session.query(Organization)
        if by_name is not None:
            qry = qry.filter(Organization.name.ilike(by_name))
        else:
            return []
        return [a_rec for a_rec in qry]

    def search_edmo(
        self,
        current_user_id: Optional[UserIDT],
        name_part: str,
        token: Optional[str] = None,
    ) -> List[EDMOOrganization]:
        """
        Organizations in EDMO with a name containing name_part, for suggesting official ones.
        Needs a logged user, or the registration token of an unlogged user creating an account.
        """
        if current_user_id is not None:
            RightsBO.get_user_throw(self.ro_session, current_user_id)
        else:
            self._is_registering_throw(token)
        return EDMOFetcher.search(name_part)

    @staticmethod
    def _is_registering_throw(token: Optional[str]) -> None:
        """
        check if unlogged user is creating an account, with the token received by email
        """
        if not token:
            raise HTTPException(status_code=403, detail=[NOT_AUTHORIZED])
        with UserService() as sce:
            sce.verify_registration_token_throw(token)

    def list(
        self,
        current_user_id: UserIDT,
        ids: OrganizationIDListT,
        fields: str = "*summary",
    ) -> List[OrganizationModel]:
        """
        List all organizations, or some of them by their ids, if requester is manager.
        """
        # TODO use fields params
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        ret = []
        # for faster display in test
        # TODO query with a join on collection manager and current user plus collectionusersroles
        qry = self.ro_session.query(Organization)
        qry = self._limit_qry(current_user, qry)
        if len(ids) > 0:
            qry = qry.filter(Organization.id.in_(ids))
        for db_org in qry:
            org = OrganizationModel(
                id=db_org.id, name=db_org.name, directories=db_org.directories
            )
            ret.append(org)
        ret = sorted(ret, key=lambda d: d.name, reverse=True)
        return ret

    def _has_ident_org(self, organization: str) -> bool:
        """
        Check if the organization name exists
        """
        is_other: Optional[Organization] = (
            self.ro_session.query(Organization.name)
            .filter(Organization.name.ilike(organization))
            .scalar()
        )
        return is_other is not None

    def _set_organization_row(
        self,
        update_src: OrganizationModel,
        org_to_update: Organization,
        cols_to_upd: List,
    ):
        """
        common to add or update an organization
        """
        if len(cols_to_upd) == 0:
            return None
        for col in cols_to_upd:
            value = getattr(update_src, col.name)
            setattr(org_to_update, col.name, value)
        self.session.commit()
        if org_to_update.id != "":
            action = ActivationType.update.name
        else:
            action = ActivationType.create.name
        logger.info("Organization %s :  '%s'" % (action, update_src.name))

    def _is_valid_org_throw(self, mod_src: OrganizationModel, _id: int):
        # check if it's a valid name
        if mod_src.name.strip() == "":
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_CANT_CHECK_VALIDITY],
            )
        # check if another organization exists with the same name
        exists = self._has_ident_org(mod_src.name)
        if exists and _id != mod_src.name:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_ALREADY_EXISTS],
            )

    def _is_manager_throw(self, user: User) -> CollectionIDListT:
        """
        check if current_user can admin guest
        """
        if not user.is_manager():
            collection_ids = CollectionBO.projects_managed_by(self.ro_session, user)
            if len(collection_ids) == 0:
                raise HTTPException(
                    status_code=403,
                    detail=[NOT_AUTHORIZED],
                )
            return collection_ids
        return []

    def _can_manage_organization_throw(self, user: User, organization: OrganizationIDT):
        """
        check if user can update organization name and directories (has to be creator_organizations or associates_organizations  in a collection managed by the user)
        """
        can_manage = CollectionBO.can_manage_organization(
            self.ro_session, user, organization
        )
        if not can_manage:
            raise HTTPException(
                status_code=403,
                detail=[NOT_AUTHORIZED],
            )
