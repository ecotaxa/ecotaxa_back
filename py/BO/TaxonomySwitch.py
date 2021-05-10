# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Switch from UniEUK (present in march 2021) taxonomy to WoRMS.
#   Data sources are Worms DB table and ToWorms manual file.
#
from typing import Dict, Tuple

from API_operations.TaxonomyService import TaxonomyService
from BO.Classification import ClassifIDListT, ClassifIDT
from BO.Taxonomy import WoRMSSetFromTaxaSet, TaxonomyBO
from DB import WoRMS
from DB.helpers.ORM import Session
from data.ToWorms import ToWorms


class TaxonomyMapper(object):
    """
        Take a set of present classification IDs and find the best possible set
        of corresponding aphia_ids.
    """

    def __init__(self, session: Session, taxon_ids: ClassifIDListT):
        self.session = session
        self.taxa_ids = set(taxon_ids)

    def do_match(self) -> Tuple[Dict[ClassifIDT, WoRMS], Dict[ClassifIDT, ClassifIDT]]:
        """
            Returns: A dict with matched Phylo taxo ids->WoRMS entry. The taxa might be Morpho ones,
                        as the XLSX data source contains such mappings.
                    + Another dict with unmatched Morpho entries.

        :return:
        """
        ret: Dict[ClassifIDT, WoRMS] = {}

        # Do the manual (i.e. XLSX-driven) matching of what can be.
        # In this part, both Morpho and Phylo taxa are matched to WoRMS.
        to_worms: ToWorms = ToWorms()
        to_worms.prepare()
        to_worms.apply()
        manual_ids = set(to_worms.done_remaps.keys()).intersection(self.taxa_ids)
        for a_manual_id in list(manual_ids):
            # Get the mapping
            aphia_id = to_worms.done_remaps[a_manual_id]
            if aphia_id is None:
                # No mapping -> re-add to auto matching to come, who knows...
                manual_ids.remove(a_manual_id)
                continue
            worms_rec = self.session.query(WoRMS).get(aphia_id)
            assert worms_rec is not None
            ret[a_manual_id] = worms_rec

        # Do auto matching of the rest
        ids_for_auto_match = self.taxa_ids.difference(manual_ids)

        # Only keep Phylo taxa, the Morpho ones will get aggregated with their nearest Phylo parent
        phylo_auto_ids = TaxonomyBO.keep_phylo(self.session, list(ids_for_auto_match))

        # Lookup parents of morpho taxa
        with TaxonomyService() as taxo_sce:
            morpho_ids = list(ids_for_auto_match.difference(phylo_auto_ids))
            # Borrow taxo tree from ToWorms which has nearly all we need.
            to_worms.add_to_unieuk(morpho_ids, taxo_sce)
            unieuk_per_id = to_worms.unieuk
            needed_parents = []
            for a_morpho_id in morpho_ids:
                for a_parent_id in unieuk_per_id[a_morpho_id].id_lineage:
                    if a_parent_id not in unieuk_per_id:
                        needed_parents.append(a_parent_id)
            to_worms.add_to_unieuk(needed_parents, taxo_sce)

        # Build morpho -> nearest phylo mapping
        phylo_per_morpho: Dict[ClassifIDT, ClassifIDT] = {}
        for a_morpho_id in morpho_ids:
            for a_parent_id in unieuk_per_id[a_morpho_id].id_lineage:
                if unieuk_per_id[a_parent_id].type == 'P':
                    phylo_per_morpho[a_morpho_id] = a_parent_id
                    if a_parent_id not in ret:
                        phylo_auto_ids.add(a_parent_id)
                    break

        # Do more matches
        ret.update(WoRMSSetFromTaxaSet(self.session, list(phylo_auto_ids)).res)

        # Sanity check
        # for an_id in ret.keys():
        #     assert unieuk_per_id[an_id].type == 'P' # Not true
        for a_morpho_id, a_phylo_id in phylo_per_morpho.items():
            assert unieuk_per_id[a_morpho_id].type == 'M'
            assert unieuk_per_id[a_phylo_id].type == 'P'

        return ret, phylo_per_morpho
