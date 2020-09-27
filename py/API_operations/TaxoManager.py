# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import tempfile
from collections import deque
from typing import Dict, Set, List

from httpx import ReadTimeout

from BO.Rights import RightsBO
from DB import Taxonomy, Role
from DB.Project import ProjectTaxoStat
from DB.WoRMs import WoRMS
from DB.helpers.ORM import Query
from DB.helpers.ORM import only_res, func
from helpers.DynamicLogs import get_logger, switch_log_to_file, switch_log_back
from providers.WoRMS import WoRMSFinder
from .helpers.Service import Service

logger = get_logger(__name__)


class TaxonomyChangeService(Service):  # pragma:nocover
    """
        A service dedicated to the move from UniEUK taxonomy referential to WoRMS one.
        Not exposed to any category of user in the app.
    """
    MAX_QUERIES = 500

    def __init__(self, max_requests: int):
        super().__init__()
        self.temp_log = ""
        # aphia_id -> all_fetched
        self.existing_id: Dict[int, bool] = {}
        self.to_fetch: deque = deque()
        self.nb_queries = 0
        if max_requests is not None:
            self.max_queries = max_requests
        else:
            self.max_queries = self.MAX_QUERIES

    def log_to_temp(self) -> str:
        self.temp_log = tempfile.NamedTemporaryFile(suffix=".log", delete=True).name
        switch_log_to_file(self.temp_log)
        return self.temp_log

    async def db_refresh(self, current_user_id: int):
        """
            Refresh the local taxonomy DB.
        """
        # Security check
        _user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        await self._do_refresh()
        switch_log_back()

    @staticmethod
    def to_latin1_compat(a_str: str):
        if a_str is None:
            return a_str
        try:
            _str_lat1 = a_str.encode("latin-1")
        except UnicodeEncodeError:
            return a_str.encode("latin-1", errors='xmlcharrefreplace')
        return a_str

    # noinspection PyPep8Naming
    def json_to_ORM(self, a_child: Dict) -> WoRMS:
        """
            Prepare a DB record from the JSON structure returned by WoRMS REST API.
        """
        to_lat1 = self.to_latin1_compat
        ret = WoRMS()
        ret.aphia_id = a_child["AphiaID"]
        ret.kingdom = a_child["kingdom"]
        ret.url = a_child["url"]
        ret.scientificname = to_lat1(a_child["scientificname"])
        ret.authority = to_lat1(a_child["authority"])
        ret.status = a_child["status"]
        ret.unacceptreason = to_lat1(a_child["unacceptreason"])
        ret.taxon_rank_id = a_child["taxonRankID"]
        ret.rank = a_child["rank"]
        ret.valid_aphia_id = a_child["valid_AphiaID"]
        ret.valid_name = a_child["valid_name"]
        ret.valid_authority = to_lat1(a_child["valid_authority"])
        ret.parent_name_usage_id = a_child["parentNameUsageID"]
        ret.kingdom = a_child["kingdom"]
        ret.phylum = a_child["phylum"]
        ret.class_ = a_child["class"]
        ret.order = a_child["order"]
        ret.family = a_child["family"]
        ret.genus = to_lat1(a_child["genus"])
        ret.citation = to_lat1(a_child["citation"])
        ret.lsid = a_child["lsid"]
        ret.is_marine = a_child["isMarine"]
        ret.is_brackish = a_child["isBrackish"]
        ret.is_freshwater = a_child["isFreshwater"]
        ret.is_terrestrial = a_child["isTerrestrial"]
        ret.is_extinct = a_child["isExtinct"]
        ret.match_type = a_child["match_type"]
        ret.modified = a_child["modified"]
        return ret

    async def _do_refresh(self):
        """
            Do the real job.
        """
        logger.info("Starting...")
        # Query all for fast existence testing
        qry = self.session.query(WoRMS.aphia_id, WoRMS.all_fetched)
        self.existing_ids = {rec[0]: rec[1] for rec in qry.all()}
        logger.info("Existing: %d entries", len(self.existing_ids))
        # What was not fetched needs to be
        self.to_fetch.extend([an_id for an_id in self.existing_ids if not self.existing_ids[an_id]])
        # Loop until all was refreshed
        while True:
            try:
                id_to_fetch = self.to_fetch.popleft()
            except IndexError:
                break
            try:
                children_ids = await self._add_children_of(id_to_fetch)
            except ResourceWarning:
                logger.warning("Limit of %d queries reached.", self.max_queries)
                break
            except ReadTimeout:
                logger.warning("Timeout for %d.", id_to_fetch)
                continue
            # Report progress
            if len(children_ids) > 0:
                logger.info("Added to DB: %s, %d queries done.", children_ids, self.nb_queries)
            # Add the children to the explore
            self.to_fetch.extend(children_ids)
        logger.info("Done, %d items remaining to fetch.", len(self.to_fetch))

    async def _add_children_of(self, parent_aphia_id: int) -> Set[int]:
        """
            Add in DB (recursively) the children of given taxon by its aphia_id.
        """
        # REST calls limit
        if self.nb_queries > self.max_queries:
            raise ResourceWarning("Not making more than %d queries", self.max_queries)
        self.nb_queries += 1
        # It looks like the parent is returned with its children
        children = await WoRMSFinder.aphia_children_by_id(parent_aphia_id)
        children_ids = set()
        for a_child in children:
            to_add = self.json_to_ORM(a_child)
            to_add.all_fetched = False
            children_ids.add(to_add.aphia_id)
            if to_add.aphia_id in self.existing_ids:
                # TODO: Update
                pass
            else:
                self.session.add(to_add)
                self.existing_ids[to_add.aphia_id] = False
        # DB persist
        if len(children_ids) > 0:
            try:
                self.session.commit()
            except Exception as e:
                logger.error("For parent %d and child %s : %s", parent_aphia_id, children_ids, e)
                self.session.rollback()
                return set()
        # Signal done
        self.session.query(WoRMS).get(parent_aphia_id).all_fetched = True
        self.session.commit()
        return children_ids

    async def _get_db_children(self, aphia_id: int):
        """
            Return the known list of children for this aphia_id 
        """
        children_qry = self.session.query(WoRMS.aphia_id)
        children_qry = children_qry.filter(WoRMS.parent_name_usage_id == aphia_id)
        children_ids = set(only_res(children_qry.all()))
        return children_ids

    # TODO: /AphiaRecordsByDate Lists all AphiaRecords (taxa) that have their last edit action (modified or added)
    #  during the specified period
    # Get max of dates in our DB as start of range

    def matching(self, _current_user_id: int) -> List[List]:
        """
            Return the list of matching entries b/w Taxonomy and WoRMS.
        """
        # No security check. TODO?
        used_taxo_ids: Query = self.session.query(ProjectTaxoStat.id).distinct()
        used_taxo_ids = used_taxo_ids.filter(ProjectTaxoStat.nbr > 0)

        qry: Query = self.session.query(Taxonomy, WoRMS)
        qry = qry.join(WoRMS, func.lower(WoRMS.scientificname) == func.lower(Taxonomy.name))
        qry = qry.filter(Taxonomy.id.in_(used_taxo_ids))
        qry = qry.order_by(func.lower(Taxonomy.name))
        # Format result
        ret = []
        for a_res in qry.all():
            taxo: Taxonomy = a_res[0]
            worms: WoRMS = a_res[1]
            line = [worms.aphia_id, worms.status, taxo.id, taxo.name, taxo.taxotype, taxo.taxostatus]
            ret.append(line)
        return ret
