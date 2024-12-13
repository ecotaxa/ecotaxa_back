# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A description of transformation to the WoRMS taxonomic system.
#
from typing import Dict, Set, Iterable, List, Optional

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
