# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2025  Picheral, Colin, Irisson (UPMC-CNRS)
#

from typing import Optional, List
from API_models.crud import OrganizationModel
from fastapi import HTTPException
from BO.Rights import RightsBO, NOT_AUTHORIZED, NOT_FOUND
from BO.User import UserIDT
from DB.Collection import CollectionUserRole
from DB.User import User, Organization, OrganizationIDT, OrganizationIDListT
from BO.Collection import CollectionBO, CollectionIDListT
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_NOT_FOUND,
    DETAIL_ALREADY_EXISTS,
    DETAIL_CANT_CHECK_VALIDITY,
)
from ..helpers.UserValidation import ActivationType
from ..helpers.Service import Service

logger = get_logger(__name__)


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
        current_user_id: UserIDT,
        new_org: OrganizationModel,
    ) -> OrganizationIDT:
        # Must be manager to create an account
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
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
        org_to_update: Optional[Organization] = self.session.query(Organization).get(
            organization
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

    def search_by_id(
        self, current_user_id: UserIDT, organization: OrganizationIDT
    ) -> Optional[Organization]:
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        # TODO: Not consistent with others e.g. project.query()
        ret = self.ro_session.query(Organization).get(organization)
        return ret

    def get_full_by_id(
        self, current_user_id: UserIDT, organization: OrganizationIDT
    ) -> OrganizationModel:
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        db_org = (
            self.ro_session.query(Organization)
            .filter(Organization.name.ilike(organization))
            .scalar()
        )
        if db_org is None:
            raise HTTPException(status_code=404, detail=DETAIL_NOT_FOUND)
        else:
            ret = OrganizationModel(
                id=db_org.id, name=db_org.name, directories=db_org.directories
            )
        return ret

    def _limit_qry(self, current_user: User, qry):
        if not current_user.is_manager():
            collection_ids = CollectionBO.projects_managed_by(
                self.ro_session, current_user
            )
            qry = qry.join(CollectionUserRole).filter(
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

    def search_organizations(self, by_name: Optional[str]) -> List[str]:
        qry = self.ro_session.query(Organization)
        if by_name is not None:
            qry = qry.filter(Organization.name.ilike(by_name))
        else:
            return []
        return [a_rec for a_rec in qry]

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
        # check if it's a valid email - check should be done before exists but has to be compatible with data history
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
