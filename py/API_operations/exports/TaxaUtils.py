# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from typing import Dict, Optional

from sqlalchemy.orm import Session

from API_operations.TaxoManager import TaxonomyChangeService
from DB import WoRMS
from DB.helpers.ORM import Query
from helpers.DynamicLogs import get_logger
from providers.WoRMS import WoRMSFinder

logger = get_logger(__name__)

ALL_RANKS = {
    "Kingdom": 1,
    "Subkingdom": 2,
    "Infrakingdom": 3,
    "Phylum": 4,
    "Class": 5,
    "Subclass": 6,
    "Order": 7,
    "Suborder": 8,
    "Family": 9,
    "Species": 10,
    "Subfamily": 11,
    "Genus": 12,
}
RANKS_BY_ID = {v: k for k, v in ALL_RANKS.items()}


class TaxonInfo(object):  # noqa: Work in progress
    """
        Taxon information.
            Collected from our DB
            + http://www.marinespecies.org/
            Note: https://www.gbif.org/tools/species-lookup
    """

    def __init__(self, name: str):
        self.name: str = name  # Our name from DB
        self.aphia_id: Optional[int] = None  # AphiaID from WoRMs
        self.rank = 0

    def is_valid(self):
        return self.aphia_id > 0

    def has_worms(self) -> bool:
        return self.aphia_id is not None


class TaxonInfoForSample(object):
    """
        Taxon information, relevant to EMODnet export.
    """

    def __init__(self, count: int):
        self.taxon_info: Optional[TaxonInfo] = None
        # Number of beasts inside the sample
        self.count: int = count


class TaxaCache(object):
    """
        Matcher
    """

    @staticmethod
    def collect_worms_for(session: Session, taxon_dict: Dict[int, str]) -> Dict[int, TaxonInfo]:
        """
            Gather WoRMS information for the entries.
        """
        ret = {}
        # Very primitive match by name
        for taxon_id, taxon_name in taxon_dict.items():
            qry: Query = session.query(WoRMS.aphia_id)
            qry = qry.filter(WoRMS.scientificname == taxon_name)
            res = qry.all()
            if res:
                ret[taxon_id] = TaxonInfo(taxon_name)
                ret[taxon_id].aphia_id = res[0]
        # Do REST call to get information
        missing_ids = set(taxon_dict.keys()).difference(ret.keys())
        for an_id in missing_ids:
            # TODO: WoRMS has batch mode, allowing several lookups in one go
            to_find = taxon_dict[an_id]
            ret[an_id] = TaxonInfo(to_find)
            # TODO: We need an accepted quality, and there might be several matches. See WoRMS API.
            aphia_rec = WoRMSFinder.aphia_records_by_name_sync(to_find)
            if len(aphia_rec) == 0:
                ret[an_id].aphia_id = -1
            else:
                worms = TaxonomyChangeService.json_to_ORM(aphia_rec[0])
                # TODO: Take values, put into DB
                ret[an_id].aphia_id = worms.aphia_id
        return ret
