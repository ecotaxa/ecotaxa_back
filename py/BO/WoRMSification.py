# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A description of transformation to the WoRMS taxonomic system.
#
from typing import Dict, Set, Iterable, List

from BO.Classification import ClassifIDT, ClassifIDListT
from BO.ObjectSetQueryPlus import TaxoRemappingT
from BO.Taxonomy import TaxonBO
from DB import WoRMS


class WoRMSifier(object):
    """
    How to go from UniEUK to WoRMS, for a set of taxa.
    The taxa might be Phylo (mapped to WoRMS) or Morpho (mapped to a Phylo itself mapped to WoRMS)
    """

    def __init__(self) -> None:
        # A dict with Phylo taxo ids->WoRMS entry. The taxa might be Morpho ones,
        #                         as the XLSX data source contains such mappings.
        self.phylo2worms: Dict[ClassifIDT, WoRMS] = {}
        # A dict with Morpho -> nearest_phylo mapping. None value means that there
        # is no "solution" for the "problem" of mapping this taxon, or that it was
        # purposing-ly discarded.
        self.morpho2phylo: TaxoRemappingT = {}

    def get_worms_targets(self) -> List[WoRMS]:
        return [v for k, v in self.phylo2worms.items()]

    def add_phylos(self, assocs: Dict[ClassifIDT, WoRMS]) -> None:
        """Add the associations from one system to the other"""
        assert assocs.keys().isdisjoint(self.phylo2worms.keys())
        self.phylo2worms.update(assocs)

    def add_morpho(self, morpho_id: ClassifIDT, phylo_id: ClassifIDT) -> None:
        """Store Morpho->Nearest Phylo relationship, knowing that we'll
        need the phylo->WoRMS"""
        self.morpho2phylo[morpho_id] = phylo_id

    def uncovered_phylo(self) -> Set[ClassifIDT]:
        """Return what is needed so that each Phylo has a WoRMS.
        - phylo2worms.keys() have one by construction,
        - morpho2phylo.values() _might_ not"""
        ret = set()
        phylo2worms = self.phylo2worms.keys()
        for a_to in self.morpho2phylo.values():
            if a_to is None or a_to in phylo2worms:
                continue
            ret.add(a_to)
        return ret

    def sanity_check(self, unieuk_per_id: Dict[ClassifIDT, TaxonBO]):
        for a_morpho_id, a_phylo_id in self.morpho2phylo.items():
            assert unieuk_per_id[a_morpho_id].type == "M"
            if a_phylo_id is None:
                continue
            assert unieuk_per_id[a_phylo_id].type == "P"

    def taxotype_sanity_check(self):
        """Sanity check: no mapped P taxon is present anymore in the transformation to WoRMS"""
        assert set(self.phylo2worms.keys()).isdisjoint(set(self.morpho2phylo.keys()))

    def apply_recast(self, recast: TaxoRemappingT):
        recast = recast.copy()  # We destroy it, protect the arg
        full_recast: TaxoRemappingT = {}
        for from_, to_ in self.morpho2phylo.items():
            if to_ in recast:
                # The target phylo is a recast source
                new_to = recast[to_]
                if new_to is None:
                    pass  # Just to signal that it might be None, meaning "to drop"
                del recast[to_]
            elif from_ in recast:
                # The source morpho is a recast source
                # Override with provided recast, if None then drop it's OK
                new_to = recast[from_]
                del recast[from_]
            else:
                # No impact on this entry from provided recast
                new_to = to_
            full_recast[from_] = new_to
        # Re-inject what's left
        full_recast.update(recast)
        self.morpho2phylo = full_recast

    def unreferenced_ids(self, ids: Iterable[ClassifIDT]) -> ClassifIDListT:
        """Return the taxa from ids, not known in self"""
        return [
            an_id
            for an_id in ids
            if an_id not in self.phylo2worms and an_id not in self.morpho2phylo
        ]
