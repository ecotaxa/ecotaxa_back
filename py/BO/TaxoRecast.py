# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Global preferences for a user
#
from typing import Union, Optional
from sqlalchemy.orm import Session
from BO.Taxonomy import TaxonBO, WoRMSBO
from BO.ProjectSet import PermissionConsistentProjectSet
from DB.Collection import CollectionProject
from DB.Project import ProjectIDT
from DB.TaxoRecast import TaxoRecast, RecastOperation
from BO.User import UserIDT
from BO.Collection import CollectionIDT
from BO.Rights import NOT_FOUND, Action
from helpers.DynamicLogs import get_logger


logger = get_logger(__name__)


class TaxoRecastBO(object):
    """
    Operations on recast taxonomy
    """

    def __init__(self, taxorecast: TaxoRecast):
        self._taxorecast = taxorecast

    @staticmethod
    def query_recast(
        session: Session,
        current_user_id: UserIDT,
        target_id: Union[ProjectIDT, CollectionIDT],
        operation: RecastOperation,
        is_collection: bool = False,
        for_update: bool = True,
    ):
        if is_collection:
            ret = (
                session.query(CollectionProject.project_id)
                .filter(CollectionProject.collection_id == target_id)
                .all()
            )
            assert len(ret) > 0, NOT_FOUND
            project_ids = ret
        else:
            project_ids = [target_id]
        if for_update:
            action = Action.ADMINISTRATE
        else:
            action = Action.READ
        PermissionConsistentProjectSet(
            session,
            project_ids,
        ).can_be_administered_by(
            current_user_id, update_preference=False, action=action
        )
        qry = session.query(TaxoRecast)
        qry = qry.filter(TaxoRecast.operation == operation.value)
        if is_collection:
            qry = qry.filter(TaxoRecast.collection_id == target_id)
        else:
            qry = qry.filter(TaxoRecast.project_id == target_id)
        logger.info("Execute query_recast SQL : %s", str(qry))
        logger.info("Params :target_id  %s " + str(target_id), operation.value)
        return qry

    @staticmethod
    def valid_remap(val) -> Optional[str]:
        v = {k: str(vv) for k, vv in val.items() if str(vv) != k}
        vals_but_0 = set(v.values()).difference({0})
        if not set(v.keys()).isdisjoint(vals_but_0):
            vals = list(set(v.keys()).intersection(vals_but_0))
            return (
                "inconsistent taxonomy renaming, can't do remap chains or loops: common part is "
                + ",".join(vals)
            )
        return None

    @staticmethod
    def create_worms_bo(taxon: TaxonBO) -> WoRMSBO:
        # Find the kingdom in lineage
        # The lineage is leaf-to-root, so kingdom is near the end
        # "Biota" is usually at the very end (root)
        # Kingdom is the one just before "Biota"
        kingdom = None
        if taxon.lineage[-1] == "Biota":
            if len(taxon.lineage) >= 2:
                kingdom = taxon.lineage[-2]
            else:
                kingdom = ""  # No kingdom for the king of kingdoms
        return WoRMSBO(
            cat_type=taxon.type,
            cat_status=taxon.status,
            display_name=taxon.display_name,
            nb_objects=taxon.nb_objects,
            nb_children_objects=taxon.nb_children_objects,
            lineage=taxon.lineage,
            id_lineage=taxon.id_lineage,
            lineage_status=taxon.lineage_status,
            aphia_id=taxon.aphia_id,
            rank=taxon.rank,
            children=taxon.children,
            rename_id=taxon.renm_id,
            kingdom=kingdom,
        )
