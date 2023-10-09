# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A description of transformation to the WoRMS taxonomic system.
#
from typing import Dict, Optional, Set

from BO.Classification import ClassifIDT
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
        # A dict with morpho -> nearest_phylo mapping.
        self.morpho2phylo: Dict[ClassifIDT, ClassifIDT] = {}

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
        return set(self.morpho2phylo.values()).difference(self.phylo2worms.keys())

    def sanity_check(self, unieuk_per_id: Dict[ClassifIDT, TaxonBO]):
        for a_morpho_id, a_phylo_id in self.morpho2phylo.items():
            assert unieuk_per_id[a_morpho_id].type == "M"
            if a_phylo_id is None:
                continue
            assert unieuk_per_id[a_phylo_id].type == "P"
