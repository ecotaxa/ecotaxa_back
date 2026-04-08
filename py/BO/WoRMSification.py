# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A description of transformation to the WoRMS taxonomic system.
#
from typing import List, Set, Dict, Optional
from sqlalchemy.orm import Session
from BO.Classification import ClassifIDT
from BO.ObjectSetQueryPlus import TaxoRemappingT
from BO.Taxonomy import TaxonBOSet, WoRMSBO
from BO.TaxoRecast import TaxoRecastBO
from DB.Taxonomy import TaxonomyIDT, TaxoType

from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


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

    @staticmethod
    def apply_recast(taxorecast: TaxoRemappingT) -> TaxoRemappingT:
        recast = taxorecast.copy()  # We destroy it, protect the arg

        def end_of_chain(recast_idx: ClassifIDT) -> Optional[ClassifIDT]:
            visited = [recast_idx]
            ret = recast[recast_idx]
            while ret in recast:
                if ret == visited[-1]:  # length-1 cycle (self-recast)
                    return ret
                if ret in visited:
                    # Cycle detected (should not as we enforce input quality), drop the taxon
                    return None
                visited.append(ret)
                ret = recast[ret]
            return ret

        # e.g. m2p: { 84974: 83278, 84975: 83278 }
        # recast: { 83278: 72398 }
        for from_, to_ in recast.items():
            if from_ in recast:
                recast[from_] = end_of_chain(from_)
                # Note: if new_to None then drop it's OK
                continue
            if to_ in recast:
                # The _target_ (phylo) is a recast source e.g. 92012 -> 83278 and 83278 -> 72398
                # Compose the recast so become e.g. 92012 -> 72398
                recast[from_] = end_of_chain(to_)
                # Note: new_to might be None, so the taxon is dropped
        # Inject recasts but don't override rules applications
        for from_ in set(taxorecast.keys()).intersection(recast.keys()):
            del taxorecast[from_]
        taxorecast.update(recast)
        return taxorecast

    @staticmethod
    def do_wormsify(
        session: Session, taxaids: List[TaxonomyIDT]
    ) -> Dict[ClassifIDT, WoRMSBO]:
        ret = TaxonBOSet(session, taxaids)
        taxamapping: Dict[ClassifIDT, WoRMSBO] = {
            t.id: TaxoRecastBO.create_worms_bo(t)
            for t in ret.as_list()
            if t.aphia_id is not None
        }
        return taxamapping
