# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license information.
# Copyright (C) 2015-2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Switch from UniEUK (present in march 2021) taxonomy to WoRMS.
#   Data sources are Worms DB table and ToWorms manual file.
#
from typing import Dict

from BO.Classification import ClassifIDListT, ClassifIDT
from BO.Taxonomy import WoRMSSetFromTaxaSet
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

    def do_match(self) -> Dict[ClassifIDT, WoRMS]:
        ret: Dict[ClassifIDT, WoRMS] = {}
        to_worms: ToWorms = ToWorms()
        to_worms.prepare()
        to_worms.apply()
        # Do the manual matching of what can be
        manual_ids = set(to_worms.done_remaps.keys()).intersection(self.taxa_ids)
        for a_manual_id in manual_ids:
            ret[a_manual_id] = self.session.query(WoRMS).get(to_worms.done_remaps[a_manual_id])
        # Do auto matching of the rest
        auto_ids = self.taxa_ids.difference(manual_ids)
        ret.update(WoRMSSetFromTaxaSet(self.session, list(auto_ids)).res)
        return ret
