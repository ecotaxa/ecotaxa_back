# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A description of transformation to the WoRMS taxonomic system.
#
from typing import Dict, Iterable, List, Optional, Set

from sqlalchemy.orm import Session

from BO.Classification import ClassifIDT, ClassifIDListT
from BO.ObjectSetQueryPlus import TaxoRemappingT
from BO.Taxonomy import TaxonBOSet, TaxonBO
from DB.Taxonomy import TaxonomyIDT, TaxoType


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


class WoRMSifier(object):
    """
    How to go from EcoTaxa IDs to WoRMS, for a set of taxa.
    The taxa might be Phylo (mapped to WoRMS) or Morpho (mapped to a Phylo itself mapped to WoRMS)
    """

    def __init__(self) -> None:
        self.phylo2worms: Dict[ClassifIDT, WoRMSBO] = {}
        self.morpho2phylo: Dict[ClassifIDT, Optional[ClassifIDT]] = {}

    def do_match(self, session: Session, taxa_ids: List[TaxonomyIDT]):
        taxon_set = TaxonBOSet(session, taxa_ids)
        # Get all parent ids
        parent_ids: Set[ClassifIDT] = set()
        for a_taxon in taxon_set.as_list():
            parent_ids.update(a_taxon.id_lineage[:-1])
        parent_taxon_set = TaxonBOSet(session, list(parent_ids))
        # And all target renames
        rename_ids: Set[ClassifIDT] = set()
        for a_taxon in taxon_set.as_list():
            if a_taxon.renm_id is not None:
                rename_ids.add(a_taxon.renm_id)
        renamed_taxon_set = TaxonBOSet(session, list(rename_ids))

        def create_worms_bo(taxon: TaxonBO) -> WoRMSBO:
            # Find the kingdom in lineage
            # The lineage is leaf-to-root, so kingdom is near the end
            # "Biota" is usually at the very end (root)
            # Kingdom is the one just before "Biota"
            kingdom = None
            if len(taxon.lineage) >= 2:
                if taxon.lineage[-1] == "Biota":
                    kingdom = taxon.lineage[-2]
                else:
                    kingdom = taxon.lineage[-1]
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

        # Get closest phylos for morphos
        for a_taxon in taxon_set.as_list():
            if not a_taxon.type == TaxoType.morpho:
                continue
            for parent_id in a_taxon.id_lineage[1:]:
                if parent_taxon_set.get_by_id(parent_id).type != TaxoType.morpho:
                    self.morpho2phylo[a_taxon.id] = parent_id
                    break
            else:
                self.morpho2phylo[a_taxon.id] = None  # Can't resolve
        # Get closest WoRMS for phylos
        for a_taxon in taxon_set.as_list():
            if not a_taxon.type == TaxoType.phylo:
                continue
            if a_taxon.aphia_id is not None:
                self.phylo2worms[a_taxon.id] = create_worms_bo(a_taxon)
            elif a_taxon.renm_id is not None:
                renamed_taxon = renamed_taxon_set.get_by_id(a_taxon.renm_id)
                self.phylo2worms[a_taxon.id] = create_worms_bo(renamed_taxon)
            # No solution, excluded taxon, will be signaled during export

    def get_worms_targets(self) -> List[WoRMSBO]:
        return list(self.phylo2worms.values())

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

    def unreferenced_ids(self, ids: Iterable[ClassifIDT]) -> ClassifIDListT:
        """Return the taxa from ids, not known in self"""
        return [
            an_id
            for an_id in ids
            if an_id not in self.phylo2worms and an_id not in self.morpho2phylo
        ]
