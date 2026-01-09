# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A description of transformation to the WoRMS taxonomic system.
#
from typing import Dict, Any, Iterable, List, Optional
from BO.Classification import ClassifIDT, ClassifIDListT
from BO.ObjectSetQueryPlus import TaxoRemappingT
from BO.Taxonomy import TaxonBOSet
from DB.Taxonomy import Taxonomy, TaxonomyIDT, TaxoStatus, TaxoType
from sqlalchemy.orm import Session


class WoRMSifier(object):
    """
    How to go from UniEUK to WoRMS, for a set of taxa.
    The taxa might be Phylo (mapped to WoRMS) or Morpho (mapped to a Phylo itself mapped to WoRMS)
    """

    def __init__(self) -> None:
        self.morpho2phylo = {}
        self.phylo2worms = {}

    def do_match(self, session: Session, taxaids: List[TaxonomyIDT]) -> List[Taxonomy]:
        self.taxonboset = TaxonBOSet(session, taxaids)


    def get_worms_targets(self) -> List[Dict[str, Any]]:
        worms_targets = [
            {
                "id": r.worms_mapping[0],
                "aphia_id": r.worms_mapping[1],
                "name": r.worms_mapping[2],
                "rank": r.worms_mapping[3],
            }
            for r in self.taxonboset.taxa
            if r.worms_mapping is not None
        ]
        return worms_targets

    def apply_recast(self, recast: TaxoRemappingT) -> None:
        recast = recast.copy()  # We destroy it, protect the arg

    def unreferenced_ids(self, ids: Iterable[ClassifIDT]) -> ClassifIDListT:
        """Return the taxa from ids, not known in self"""
        return [
            an_id
            for an_id in ids
            if an_id not in self.phylo2worms and an_id not in self.morpho2phylo
        ]
