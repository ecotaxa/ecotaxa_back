# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union, Optional

from API_models.crud import CreateCollectionReq
from BO.Collection import CollectionBO, CollectionIDT
from BO.Rights import RightsBO, NOT_FOUND
from BO.User import UserIDT
from DB.Collection import Collection
from DB.User import Role
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service

logger = get_logger(__name__)


class CollectionsService(Service):
    """
        Basic CRUD operations on Collections
    """

    def create(self, current_user_id: UserIDT, req: CreateCollectionReq) -> Union[CollectionIDT, str]:
        """
            Create a collection.
        """
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        coll_id = CollectionBO.create(self.session, req.title, req.project_ids)
        return coll_id

    def search(self, current_user_id: UserIDT, title: str) -> List[CollectionBO]:
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        qry = self.ro_session.query(Collection).filter(Collection.title.ilike(title))
        ret = [CollectionBO(a_rec).enrich() for a_rec in qry]
        return ret

    def query(self, current_user_id: UserIDT, coll_id: CollectionIDT, for_update: bool) -> Optional[CollectionBO]:
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        ret = CollectionBO.get_one(self.session if for_update else self.ro_session, coll_id)
        return ret

    def query_by_title(self, title: str) -> CollectionBO:
        # Return a unique collection from its title
        qry = self.ro_session.query(Collection).filter(Collection.title == title)
        ret = [CollectionBO(a_rec).enrich() for a_rec in qry]
        assert len(ret) == 1, NOT_FOUND
        return ret[0]

    def query_by_short_title(self, title: str) -> CollectionBO:
        # Return a unique collection from its title, short one
        qry = self.ro_session.query(Collection).filter(Collection.short_title == title)
        ret = [CollectionBO(a_rec).enrich() for a_rec in qry]
        assert len(ret) == 1, NOT_FOUND
        return ret[0]

    def delete(self, current_user_id: UserIDT, coll_id: CollectionIDT) -> int:
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        CollectionBO.delete(self.session, coll_id)
        self.session.commit()
        return 0
