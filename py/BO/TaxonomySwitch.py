# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Switch from UniEUK (present in march 2021) taxonomy to WoRMS.
#   Data sources are Worms DB table and ToWorms manual file.
#
from typing import Dict

from API_operations.TaxonomyService import TaxonomyService
from BO.Classification import ClassifIDListT, ClassifIDT
from BO.Taxonomy import StrictWoRMSSetFromTaxaSet, TaxonomyBO
from BO.WoRMSification import WoRMSifier
from DB.WoRMs import WoRMS
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

    def do_match(
        self,
    ) -> WoRMSifier:
        ret = WoRMSifier()

        # Do the manual (i.e. XLSX-driven) matching of what can be.
        # In this part, both Morpho and Phylo taxa are matched to WoRMS.
        to_worms: ToWorms = ToWorms()
        # Load & QC data
        pbs = to_worms.pre_validate()
        # TODO
        # assert pbs == []
        to_worms.prepare()
        to_worms.validate_with_trees()
        to_worms.show_stats()
        # Apply
        to_worms.apply()
        # Some taxa have a directly declared (in ToWoRMs, i.e. in golden XLSX) correspondance
        # ⚠ These might be Morpho ones? Or not... TODO: Check
        direct_ids = set(to_worms.done_remaps.keys()).intersection(self.taxa_ids)
        for a_direct_id in list(direct_ids):
            # Get the mapping
            aphia_id = to_worms.done_remaps[a_direct_id]
            if aphia_id is None:
                # TODO: The conditions under which we have no target are unclear, I guess it's due to the XLSX being inconsistent?
                # No mapping -> re-add to auto matching to come, who knows...
                direct_ids.remove(a_direct_id)
                continue
            worms_rec = self.session.query(WoRMS).get(aphia_id)
            assert worms_rec is not None
            ret.add_phylos({a_direct_id: worms_rec})

        # Do "auto" matching of the rest
        ids_for_auto_match = self.taxa_ids.difference(direct_ids)

        # Split in two sets, the Phylo and the Morpho ones
        phylo_auto_ids = TaxonomyBO.keep_phylo(self.session, list(ids_for_auto_match))
        morpho_auto_ids = list(ids_for_auto_match.difference(phylo_auto_ids))

        # Update then borrow taxo tree from ToWorms which has nearly all we need, but is partial
        with TaxonomyService() as taxo_sce:
            to_worms.add_to_unieuk_with_lineage(morpho_auto_ids, taxo_sce)
            unieuk_per_id = to_worms.unieuk

        # Store morpho -> nearest phylo mapping
        for a_morpho_id in morpho_auto_ids:
            # Climbing up the taxo tree, we have e.g. M1 -> M2 -> M3 ... -> P then only P until root
            for a_parent_id in unieuk_per_id[a_morpho_id].id_lineage:
                if unieuk_per_id[a_parent_id].type == "P":
                    # Add e.g. M1 -> P
                    ret.add_morpho(a_morpho_id, a_parent_id)
                    break

        # Do more matches
        phylo_auto_ids.update(ret.uncovered_phylo())
        strict_matches: Dict[ClassifIDT, WoRMS] = StrictWoRMSSetFromTaxaSet(
            self.session, list(phylo_auto_ids)
        ).res
        ret.add_phylos(strict_matches)

        ret.sanity_check(unieuk_per_id)

        to_worms.check_ancestors()
        to_worms.check_closure()
        to_worms.check_sums()

        return ret
