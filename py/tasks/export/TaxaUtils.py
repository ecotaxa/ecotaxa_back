import pickle
from typing import Dict, Iterable, Optional, List

from sqlalchemy.orm import Session

from db.Taxonomy import Taxonomy
from tasks.WoRMSFinder import WoRMSFinder
from tech.DynamicLogs import get_logger

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


class TaxonInfo(object):
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

    def from_worms_api(self, worms: List[Dict]):
        """ { "AphiaID": 1080,
              "url": "http://www.marinespecies.org/aphia.php?p=taxdetails&id=1080",
              "scientificname": "Copepoda",
              "authority": "Milne Edwards, 1840",
              "status": "accepted",
              "unacceptreason": null,
              "taxonRankID": 70,
              "rank": "Subclass",
              "valid_AphiaID": 1080,
              "valid_name": "Copepoda",
              "valid_authority": "Milne Edwards, 1840",
              "parentNameUsageID": 889925,
              "kingdom": "Animalia",
              "phylum": "Arthropoda",
              "class": "Hexanauplia",
              "order": null,
              "family": null,
              "genus": null,
              "citation": "WoRMS (2020). Copepoda. Accessed at: http://www.marinespecies.org/aphia.php?
                        p=taxdetails&id=1080 on 2020-06-20",
              "lsid": "urn:lsid:marinespecies.org:taxname:1080",
              "isMarine": 1,
              "isBrackish": 1,
              "isFreshwater": 1,
              "isTerrestrial": null,
              "isExtinct": null,
              "match_type": "exact",
              "modified": "2016-11-30T12:36:48.403Z"
            }
        """
        if len(worms) == 0:
            self.aphia_id = -1
            return
        if len(worms) > 1:
            # TODO: Several matches
            self.aphia_id = -1
            return
        worms = worms[0]
        if worms["status"] != "accepted":
            # TODO: Not accepted
            self.aphia_id = -1
            return
        self.aphia_id = worms["AphiaID"]
        txt_rank = worms["rank"]
        try:
            self.rank = ALL_RANKS[txt_rank]
        except KeyError:
            logger.error("Unknown rank id %s", txt_rank)


class TaxonInfoForSample(object):
    """
        Taxon information, relevant to EMODnet export.
    """

    def __init__(self, count: int):
        self.taxon_info: Optional[TaxonInfo] = None
        self.count: int = count


class TaxaCache(object):
    """
        In memory table of recent taxa.
    """
    finder_meth = WoRMSFinder.aphia_records_by_name_sync

    CACHE_FILENAME = "taxon_cache.pck"

    def __init__(self):
        self.cache: Dict[int, TaxonInfo] = {}

    def load(self):
        # TODO: Obviously not thread-safe!
        try:
            with open(self.CACHE_FILENAME, "rb") as fd:
                self.cache = pickle.load(fd)
        except (FileNotFoundError, EOFError):
            self.cache = {}

    def save(self):
        with open(self.CACHE_FILENAME, "wb") as fd:
            pickle.dump(self.cache, fd)

    def __contains__(self, key):
        return key in self.cache

    def get(self, an_id) -> TaxonInfo:
        return self.cache[an_id]

    def gather_names_for(self, session: Session, taxon_id_list: Iterable[int]):
        """
            Gather names from DB for the missing entries.
        """
        missing_ids = [taxon_id for taxon_id in taxon_id_list
                       if taxon_id not in self.cache]
        if len(missing_ids) == 0:
            return
        # Enrich with names from DB
        names = Taxonomy.names_for(session, missing_ids)
        for an_id, a_name in names.items():
            self.cache[an_id] = TaxonInfo(a_name)

    def collect_worms_for(self, taxon_id_list: Iterable[int]):
        """
            Gather WoRMS information for the missing entries.
        """
        missing_ids = [taxon_id for taxon_id in taxon_id_list
                       if not self.cache[taxon_id].has_worms()]
        if len(missing_ids) == 0:
            return
        # Do REST call to get information
        for an_id in missing_ids:
            an_info = self.cache[an_id]
            # TODO: WoRMS has batch mode, allowing several lookups in one go
            to_find = an_info.name
            # TODO: We need an accepted quality, and there might be several matches. See WoRMS API.
            ret = self.finder_meth(to_find)
            an_info.from_worms_api(ret)
