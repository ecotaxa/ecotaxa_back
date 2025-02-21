# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union, Optional, Dict, Any
from fastapi import HTTPException
from API_models.crud import CreateCollectionReq, CollectionAggregatedRsp
from API_models.exports import TaxonomyRecast
from BO.Collection import CollectionBO, CollectionIDT
from BO.ProjectSet import PermissionConsistentProjectSet
from BO.Rights import NOT_FOUND
from BO.User import UserIDT
from BO.Project import CollectionProjectBOSet
from DB.Project import ProjectIDListT
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

    def update(
        self,
        current_user_id: UserIDT,
        collection_id: CollectionIDT,
        req: Dict[str, Any],
    ):
        """
        Update a collection.
        """
        if "project_ids" in req:
            PermissionConsistentProjectSet(
                self.session, req["project_ids"]
            ).can_be_administered_by(current_user_id)
        present_collection = self.query(current_user_id, collection_id, for_update=True)
        if present_collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        present_collection.update(session=self.session, collection_update=req)

    def list(
        self, current_user_id: UserIDT, collection_ids: Optional[str] = None
    ) -> List[CollectionBO]:
        qry = self.ro_session.query(Collection)
        if collection_ids is not None:
            ids = collection_ids.split(",")
            if len(ids) > 0:
                qry = qry.where(Collection.id.in_(ids))
        ret = []
        for a_rec in qry:
            coll_bo = CollectionBO(a_rec)
            coll_bo._read_composing_projects()
            checked = self._check_access(current_user_id, coll_bo.project_ids)
            if checked is None:
                continue
            coll_bo.enrich()
            ret.append(coll_bo)
        return ret

    def search(self, current_user_id: UserIDT, title: str) -> List[CollectionBO]:
        qry = self.ro_session.query(Collection).filter(Collection.title.ilike(title))
        ret = []
        for a_rec in qry:
            coll_bo = CollectionBO(a_rec)
            coll_bo._read_composing_projects()
            checked = self._check_access(current_user_id, coll_bo.project_ids)
            if checked is None:
                continue
            coll_bo.enrich()
            ret.append(coll_bo)
        return ret

    def query(
        self, current_user_id: UserIDT, coll_id: CollectionIDT, for_update: bool
    ) -> Optional[CollectionBO]:
        ret = CollectionBO.get_one(
            self.session if for_update else self.ro_session, coll_id
        )
        if ret is None:
            return ret
        check = self._check_access(current_user_id, ret.project_ids)
        if check is None:
            return None
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

    def _check_access(
        self, user_id: UserIDT, project_ids: ProjectIDListT
    ) -> Optional[ProjectIDListT]:
        """
        Quick & dirty access check by catching the exception.
        """
        try:
            PermissionConsistentProjectSet(
                self.ro_session,
                project_ids,  # Need the R/W session here, as the projects MRU is written to. TODO
            ).can_be_administered_by(user_id, update_preference=False)
        except AssertionError:
            return None
        return project_ids

    def aggregated_from_projects(
        self,
        current_user_id: UserIDT,
        project_ids: ProjectIDListT,
    ) -> CollectionAggregatedRsp:

        projectset = CollectionProjectBOSet(
            session=self.ro_session, prj_ids=project_ids
        )
        excluded: Dict[str, ProjectIDListT] = {}
        can_be_administered = False
        try:
            PermissionConsistentProjectSet(
                self.ro_session,
                project_ids,
            ).can_be_administered_by(current_user_id, update_preference=False)
            can_be_administered = True
        except AssertionError:
            pass
        initclassiflist = projectset.get_initclassiflist_from_projects()
        classiffieldlist = projectset.get_classiffieldlist_from_projects()
        creator_users = projectset.get_annotators_from_histo(self.ro_session)
        privileges = projectset.get_privileges_from_projects()
        datas: Dict[str, Any] = {}
        datas["access"] = projectset.get_access_from_projects()
        excluded["access"] = datas["access"][1]
        datas["access"] = datas["access"][0]
        datas["status"] = projectset.get_status_from_projects()
        excluded["status"] = datas["status"][1]
        datas["status"] = datas["status"][0]
        for column in ["cnn_network_id", "instrument"]:
            datas[column] = projectset.get_common_from_projects(column)
            excluded[column] = datas[column][1]
            datas[column] = datas[column][0]
        freecols = projectset.get_mapping_from_projects()
        datas["freecols"] = {}
        for key, cols in freecols.items():
            datas["freecols"][key] = dict(freecols[key])
        aggregated: CollectionAggregatedRsp = CollectionAggregatedRsp(
            can_be_administered=can_be_administered,
            initclassiflist=initclassiflist,
            classiffieldlist=classiffieldlist,
            creator_users=creator_users,
            privileges=privileges,
            access=datas["access"],
            cnn_network_id=datas["cnn_network_id"] or "",
            instrument=datas["instrument"] or "",
            status=datas["status"] or "",
            freecols=datas["freecols"],
            excluded=excluded,
        )
        return aggregated
