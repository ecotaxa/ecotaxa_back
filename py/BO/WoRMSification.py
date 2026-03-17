# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A description of transformation to the WoRMS taxonomic system.
#
from typing import Dict, List, Optional, Set, Union
from sqlalchemy.orm import Session

from BO.Classification import ClassifIDT
from BO.Taxonomy import TaxonBOSet, TaxonBO
from DB.Taxonomy import TaxonomyIDT, TaxoType
from BO.ProjectSet import PermissionConsistentProjectSet
from DB.Collection import CollectionProject
from DB.Project import ProjectIDT
from DB.TaxoRecast import TaxoRecast, RecastOperation
from BO.User import UserIDT
from BO.Collection import CollectionIDT
from BO.ObjectSetQueryPlus import TaxoRemappingT
from BO.Rights import NOT_FOUND, Action
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class WoRMSBO(TaxonBO):
    __slots__ = ["kingdom"]

    def __init__(
        self,
        cat_type: str,
        cat_status: str,
        display_name: str,
        nb_objects: int,
        nb_children_objects: int,
        lineage: List[str],
        id_lineage: List[ClassifIDT],
        lineage_status: str,
        aphia_id: Optional[int] = None,
        rank: Optional[str] = None,
        children: Optional[List[ClassifIDT]] = None,
        rename_id: Optional[int] = None,
        kingdom: Optional[str] = None,
    ):
        super().__init__(
            cat_type,
            cat_status,
            display_name,
            nb_objects,
            nb_children_objects,
            lineage,
            id_lineage,
            lineage_status,
            aphia_id,
            rank,
            children,
            rename_id,
        )
        self.kingdom = kingdom

    def __repr__(self):
        return f"WoRMSBO({self.id}: {self.display_name}, aphia={self.aphia_id}, rank={self.rank}, kingdom={self.kingdom})"


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


class WoRMSifier(object):
    """
    How to go from EcoTaxa IDs to WoRMS, for a set of taxa.
    The taxa might be Phylo (mapped to WoRMS) or Morpho (mapped to a Phylo itself mapped to WoRMS)
    """

    def __init__(self) -> None:
        # A dict with Phylo taxo ids->WoRMS entry.
        self.phylo2worms: TaxoRemappingT = {}
        # A dict with Morpho -> nearest_phylo mapping. None value means that there
        # is no "solution" for the "problem" of mapping this taxon, or that it was
        # purposing-ly discarded.
        self.morpho2phylo: TaxoRemappingT = {}

    def do_match(self, session: Session, taxaids: List[TaxonomyIDT]):
        req_taxon_list = TaxonBOSet(session, taxaids).as_list()
        # Get all parent ids
        parent_ids: Set[ClassifIDT] = set()
        for a_taxon in req_taxon_list:
            parent_ids.update(a_taxon.id_lineage[1:])
        parent_taxon_set = TaxonBOSet(session, list(parent_ids))

        # Get closest phylos for morphos
        added_phylos = set(taxaids)
        for a_taxon in req_taxon_list:
            if not a_taxon.type == TaxoType.morpho:
                continue
            for parentid in a_taxon.id_lineage[1:]:
                parent = parent_taxon_set.get_by_id(parentid)
                if parent.type != TaxoType.morpho:
                    self.morpho2phylo[a_taxon.id] = parentid
                    added_phylos.add(parentid)
                    break
            else:
                self.morpho2phylo[a_taxon.id] = None  # Can't resolve
        added_phylos_list = TaxonBOSet(session, list(added_phylos)).as_list()

        # And all target renames
        renameids: Set[ClassifIDT] = set()
        for a_taxon in req_taxon_list + added_phylos_list:
            if a_taxon.renm_id is not None:
                renameids.add(a_taxon.renm_id)
        # Get closest WoRMS for phylos
        for a_taxon in req_taxon_list + added_phylos_list:
            if a_taxon.type == TaxoType.phylo:
                if a_taxon.aphia_id is not None:  # Closest WoRMS is self
                    self.phylo2worms[a_taxon.id] = a_taxon.id
                elif a_taxon.renm_id is not None:
                    self.phylo2worms[a_taxon.id] = a_taxon.renm_id
                else:
                    logger.warning("No solution for Phylo %s", a_taxon)
            else:
                if a_taxon.renm_id is not None:
                    self.morpho2phylo[a_taxon.id] = a_taxon.renm_id
                else:
                    logger.warning("No solution for Morpho %s", a_taxon)
                # No solution, excluded taxon, will be signaled during export
        logger.info("Mapping phylo2worms: %s", self.phylo2worms)
        logger.info("Mapping morpho2phylo: %s", self.morpho2phylo)

    def apply_recast(self, recast: TaxoRemappingT) -> None:
        recast = recast.copy()  # We destroy it, protect the arg

        def end_of_chain(recast_idx: ClassifIDT) -> Optional[ClassifIDT]:
            ret = recast[recast_idx]
            if ret in recast:
                ret = end_of_chain(ret)  # Infinite loop ->stack issue
            return ret

        # e.g. m2p: { 84974: 83278, 84975: 83278 }
        # recast: { 83278: 72398 }
        present_morpho2phylo: TaxoRemappingT = self.morpho2phylo.copy()
        for from_, to_ in present_morpho2phylo.items():
            if from_ in recast:
                # The _source_ (morpho) is a recast source e.g. 84975 -> 83278 but 84975 -> 72398
                # Override with recast so become e.g. 84975 -> 72398
                present_morpho2phylo[from_] = end_of_chain(from_)
                # Note: if new_to None then drop it's OK
                continue
            if to_ in recast:
                # The _target_ (phylo) is a recast source e.g. 92012 -> 83278 and 83278 -> 72398
                # Compose the recast so become e.g. 92012 -> 72398
                present_morpho2phylo[from_] = end_of_chain(to_)
                # Note: new_to might be None, so the taxon is dropped
        # Inject recasts but don't override rules applications
        for from_ in set(recast.keys()).intersection(present_morpho2phylo.keys()):
            del recast[from_]
        present_morpho2phylo.update(recast)
        self.morpho2phylo = present_morpho2phylo

    @staticmethod
    def do_wormsify(
        session: Session, taxaids: List[TaxonomyIDT]
    ) -> Dict[ClassifIDT, WoRMSBO]:
        ret = TaxonBOSet(session, taxaids)
        taxamapping: Dict[ClassifIDT, WoRMSBO] = {
            t.id: create_worms_bo(t) for t in ret.as_list()
        }
        return taxamapping

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
        qry = qry.filter(TaxoRecast.operation == operation)
        if is_collection:
            qry = qry.filter(TaxoRecast.collection_id == target_id)
        else:
            qry = qry.filter(TaxoRecast.project_id == target_id)
        return qry
