# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from typing import Optional, List

from fastapi import HTTPException
from API_models.crud import GuestModel
from BO.Rights import RightsBO, NOT_AUTHORIZED, NOT_FOUND
from BO.User import GuestBO,GuestIDT, GuestIDListT, UserIDT
from DB.Collection import CollectionUserRole,CollectionProject
from BO.Collection import CollectionIDListT
from BO.ProjectPrivilege import ProjectPrivilegeBO
from DB.ProjectPrivilege import ProjectPrivilege
from DB.User import Person, User, Guest
from providers.MailProvider import MailProvider
from helpers import DateTime
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_CANT_CHECK_VALIDITY,
    DETAIL_INVALID_EMAIL,
    DETAIL_EMAIL_OWNED_BY_OTHER,
    DETAIL_NOT_FOUND,
)

from ..helpers.Service import Service
from ..helpers.UserValidation import ActivationType

logger = get_logger(__name__)


class GuestService(Service):
    """
    Basic CRUD API_operations on Guest
    """

    UPDATABLE_COLS = [
        Guest.email,
        Guest.name,
        Guest.organisation,
        Guest.country,
        Guest.orcid,
    ]

    # check context to know if the email has to be verified

    def create_guest(
        self,
        current_user_id: UserIDT,
        new_guest: GuestModel,
        ) -> GuestIDT:
        # Must be manager to create an account
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        # check valid user
        self._is_valid_person_throw(new_guest, -1)
        if new_guest.id is None:
            new_guest.id = -1
        guest = Guest()
        self.session.add(guest)
        cols_to_upd = self.UPDATABLE_COLS
        self._set_guest_row(
            new_guest,
            guest,
            cols_to_upd=cols_to_upd,
        )
        return guest.id

    def update_guest(
        self,
        current_user_id: UserIDT,
        guest_id: GuestIDT,
        update_src: GuestModel,
    ) -> None:
        """
        Update a guest, who can be any guest of one of my collections if I'm an app manager.
        """
        # current_user: Optional[User] = self.ro_session.query(User).get(current_user_id)
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        self._can_manage_guest_throw(current_user, guest_id)
        guest_to_update: Optional[Guest] = self.session.query(Guest).get(guest_id)
        if guest_to_update is None:
            raise HTTPException(status_code=422, detail=[NOT_FOUND])
        self._is_valid_person_throw(update_src, guest_to_update.id)
        cols_to_upd = self.UPDATABLE_COLS
        self._set_guest_row(
            update_src,
            guest_to_update,
            cols_to_upd=cols_to_upd,
        )
        logger.info("Guest profile update %s :  '%s'" % (update_src.email, guest_id))

    def search_by_id(
        self, current_user_id: UserIDT, guest_id: GuestIDT
    ) -> Optional[Guest]:
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        # TODO: Not consistent with others e.g. project.query()
        ret = self.ro_session.query(Guest).get(guest_id)
        return ret

    def get_full_by_id(
        self, current_user_id: UserIDT, guest_id: GuestIDT
    ) -> GuestModel:
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        db_guest = self.ro_session.query(Guest).get(guest_id)
        if db_guest is None:
            raise HTTPException(status_code=404, detail=DETAIL_NOT_FOUND)
        else:
            ret = self._get_guest_profile(db_guest)
        return ret
    @staticmethod
    def _get_guest_profile(db_guest: Guest) -> GuestModel:
        ret = GuestModel.from_orm(db_guest)
        return ret

    def search(self, current_user_id: UserIDT, by_name: Optional[str]) -> List[Guest]:
        current_user = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        qry = self.ro_session.query(Guest)
        if by_name is not None:
            qry = qry.filter(Guest.name.ilike(by_name))
        else:
            return []
        return [a_rec for a_rec in qry]

    def list(
        self,
        current_user_id: UserIDT,
        guest_ids: GuestIDListT,
        fields: str = "*summary",
    ) -> List[GuestModel]:
        """
        List all guests, or some of them by their ids, if requester is manager.
        """
        #TODO use fields params
        current_user: User = RightsBO.get_user_throw(self.ro_session, current_user_id)
        self._is_manager_throw(current_user)
        ret = []
        # for faster display in test
        #TODO query with a join on collection manager and current user plus collectionusersroles
        qry = self.ro_session.query(Guest)
        if len(guest_ids) > 0:
            qry = qry.filter(Guest.id.in_(guest_ids))
        for db_guest in qry:
            ret.append(self._get_guest_profile(db_guest))
        ret = sorted(ret, key=lambda d: d.id, reverse=True)
        return ret

    def _has_ident_person_throw(self, person_data: dict, _id: int = -1) -> None:
        """
        Exception if the mail exists and id!=person_data["id"]
        """
        detail = []
        if "email" not in person_data.keys():
            detail = [DETAIL_CANT_CHECK_VALIDITY]
        else:
            is_other: Optional[Person] = GuestBO.has_ident_person(
                self.ro_session, person_data, _id
            )
            if is_other is not None:
                detail = [DETAIL_EMAIL_OWNED_BY_OTHER]
        if len(detail):
            raise HTTPException(
                status_code=422,
                detail=detail,
            )

    def _set_guest_row(self,
        update_src: GuestModel,
        guest_to_update: Guest,
        cols_to_upd: List,
          ):
        """
        common to add or update a guest
        """
        if len(cols_to_upd) == 0:
            return None
        errors: List[str] = GuestBO.check_fields(update_src.__dict__, GuestBO.to_check)
        assert len(errors) == 0, errors
        for col in cols_to_upd:
            if update_src.id == -1 and col.name == Guest.usercreationdate.name:
                value = DateTime.now_time()
            else:
                value = getattr(update_src,col.name)
            setattr(guest_to_update, col.name, value)
        self.session.commit()
        if guest_to_update.id>0:
            action=ActivationType.update.name
        else:
            action = ActivationType.create.name
        logger.info("Guest %s :  '%s'" % (action, guest_to_update.email))

    def _is_valid_person_throw(self, mod_src: GuestModel, guest_id: int) :
        # check if it's a valid email - check should be done before exists but has to be compatible with data history
        if mod_src.name == "" or str(mod_src.organisation or "") == "":
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_CANT_CHECK_VALIDITY],
            )
        elif not MailProvider.is_email(mod_src.email):
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_INVALID_EMAIL],
            )
        # check if another user exists with the same new name or new email
        self._has_ident_person_throw(
            mod_src.__dict__,
            guest_id,
        )

    def _is_manager_throw(self,user: User)->CollectionIDListT:
        """
        check if current_user can admin guest
        """
        if not user.is_manager():
           collection_ids=self._projects_managed_by(user)
           if len(collection_ids)==0:
                    raise HTTPException(
                    status_code=403,
                 detail=[NOT_AUTHORIZED],
                )
           return collection_ids
        return []


    def _projects_managed_by(self,user:User)->CollectionIDListT:
       qry=self.ro_session.query(CollectionProject.collection_id.projid).join(CollectionProject,CollectionProject.project_id == ProjectPrivilege.projid).filter(ProjectPrivilege.member == user.id).filter(ProjectPrivilege.privilege==ProjectPrivilegeBO)
       print('qry ppall============', qry.statement)
       collection_ids = qry.all()
       return collection_ids

    def _can_manage_guest_throw(self,user:User,guest_id:GuestIDT):
        """
        check if user can update guest profile (has to be creator_users or associates_users  in a collection managed by the user)
        """
        collection_ids=self._is_manager_throw(user)
        if user.is_manager():
            return
        qry= self.ro_session.query(CollectionUserRole.collection_id).filter(CollectionUserRole.collection_id.in_(collection_ids)).filter(CollectionUserRole.user_id==guest_id)
        can_manage= qry.scalar()
        if can_manage is not None:
            return
        raise HTTPException(
                status_code=403,
                detail=[NOT_AUTHORIZED],
            )


