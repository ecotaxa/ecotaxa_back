# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union, Tuple, Optional

from API_models.crud import CreateCollectionReq
from BO.ObjectSet import EnumeratedObjectSet
from BO.Collection import CollectionBO, CollectionIDListT, CollectionIDT
from BO.Rights import RightsBO, Action
from BO.User import UserIDT
from DB import Sample
from DB.Collection import Collection
from DB.User import User, Role
from DB.helpers.ORM import clone_of
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service

logger = get_logger(__name__)


class CollectionsService(Service):
    """
        Basic CRUD API_operations on Collections
    """

    def create(self, current_user_id: int,
               req: CreateCollectionReq) -> Union[int, str]:
        """
            Create a collection.
        """
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        coll = Collection()
        coll.title = req.title
        self.session.add(coll)
        self.session.flush()  # to get the collection ID
        self.session.commit()
        return coll.id

    def query(self, current_user_id: UserIDT,
              coll_id: CollectionIDT) -> Optional[CollectionBO]:
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        ret = CollectionBO.get_one(self.session, coll_id)
        return ret

    def delete(self, current_user_id: UserIDT,
               coll_id: CollectionIDT) -> int:
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        CollectionBO.delete(self.session, coll_id)
        self.session.commit()
        return 0
