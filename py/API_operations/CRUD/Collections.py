# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union, Optional

from API_models.crud import CreateCollectionReq
from API_models.exports import TaxonomyRecast
from BO.Collection import CollectionBO, CollectionIDT
from BO.ProjectSet import PermissionConsistentProjectSet
from BO.Rights import NOT_FOUND
from BO.User import UserIDT
from DB.Collection import Collection
from DB.TaxoRecast import DWCA_EXPORT_OPERATION
from DB.TaxoRecast import TaxoRecast
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service

logger = get_logger(__name__)


class CollectionsService(Service):
    """
    Basic CRUD operations on Collections
    """

    def create(
        self, current_user_id: UserIDT, req: CreateCollectionReq
    ) -> Union[CollectionIDT, str]:
        """
        Create a collection.
        """
        PermissionConsistentProjectSet(
            self.session, req.project_ids
        ).can_be_administered_by(current_user_id)
        coll_id = CollectionBO.create(self.session, req.title, req.project_ids)
        return coll_id

    def _check_access(
        self, a_coll: CollectionBO, user_id: UserIDT
    ) -> Optional[CollectionBO]:
        """
        Quick & dirty access check by catching the exception.
        """
        try:
            PermissionConsistentProjectSet(
                self.session,
                a_coll.project_ids,  # Need the R/W session here, as the projects MRU is written to. TODO
            ).can_be_administered_by(user_id)
        except AssertionError:
            return None
        return a_coll

    def search(self, current_user_id: UserIDT, title: str) -> List[CollectionBO]:
        qry = self.ro_session.query(Collection).filter(Collection.title.ilike(title))
        ret = []
        for a_rec in qry:
            coll_bo = CollectionBO(a_rec).enrich()
            checked = self._check_access(coll_bo, current_user_id)
            if checked is None:
                continue
            ret.append(checked)
        return ret

    def query(
        self, current_user_id: UserIDT, coll_id: CollectionIDT, for_update: bool
    ) -> Optional[CollectionBO]:
        ret = CollectionBO.get_one(
            self.session if for_update else self.ro_session, coll_id
        )
        if ret is None:
            return ret
        return self._check_access(ret, current_user_id)

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
        collection = self.query(current_user_id, coll_id, for_update=True)
        assert collection is not None, NOT_FOUND
        CollectionBO.delete(self.session, coll_id)
        self.session.commit()
        return 0

    def update_taxo_recast(
        self, current_user_id: UserIDT, coll_id: CollectionIDT, recast: TaxonomyRecast
    ):
        collection = self.query(current_user_id, coll_id, for_update=True)
        assert collection is not None, NOT_FOUND
        # Just remove and re-add
        self._query_recast_for_coll(coll_id).delete()
        new_recast = TaxoRecast()
        new_recast.collection_id = coll_id
        new_recast.operation = DWCA_EXPORT_OPERATION
        new_recast.transforms = recast.from_to
        new_recast.documentation = recast.doc if recast.doc else {}
        self.session.add(new_recast)
        self.session.commit()

    def read_taxo_recast(
        self, current_user_id: UserIDT, coll_id: CollectionIDT
    ) -> TaxonomyRecast:
        collection = self.query(current_user_id, coll_id, for_update=False)
        assert collection is not None, NOT_FOUND
        qry = self._query_recast_for_coll(coll_id)
        res = list(qry)
        assert len(res) == 1, NOT_FOUND
        the_one: TaxoRecast = res[0]
        ret = TaxonomyRecast(from_to=the_one.transforms, doc=the_one.documentation)
        return ret

    def _query_recast_for_coll(self, coll_id: CollectionIDT):
        qry = (
            self.session.query(TaxoRecast)
            .filter(TaxoRecast.collection_id == coll_id)
            .filter(TaxoRecast.operation == DWCA_EXPORT_OPERATION)
        )
        return qry
