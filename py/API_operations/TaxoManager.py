# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import io
from typing import List, Dict

from BO.Rights import RightsBO
from DB import Role
from DB.WoRMs import WoRMS
from DB.helpers.ORM import only_res
from helpers.DynamicLogs import get_logger, switch_log_to_file, switch_log_back
from providers.WoRMS import WoRMSFinder
from .helpers.Service import Service

logger = get_logger(__name__)


class TaxonomyService(Service):
    """
        Merge operation, move everything from source into destination project.
    """

    def __init__(self):
        super().__init__()

    def db_refresh(self, current_user_id: int) -> List[str]:
        """
            Refresh the local taxonomy DB.
        """
        # Security check
        user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        # OK
        # Temporary: stream logs for debugging in a navigator
        output = io.StringIO()
        switch_log_to_file(output)
        self.existing_id: Dict[int, bool] = {}
        self.nb_queries = 0
        self._do_refresh(1)
        ret = output.getvalue().split("\n")
        switch_log_back()
        return ret

    def json_to_ORM(self, a_child: Dict) -> WoRMS:
        ret = WoRMS()
        ret.aphia_id = a_child["AphiaID"]
        ret.kingdom = a_child["kingdom"]
        ret.url = a_child["url"]
        ret.scientificname = a_child["scientificname"]
        ret.authority = a_child["authority"]
        ret.status = a_child["status"]
        ret.unacceptreason = a_child["unacceptreason"]
        ret.taxon_rank_id = a_child["taxonRankID"]
        ret.rank = a_child["rank"]
        ret.valid_aphia_id = a_child["valid_AphiaID"]
        ret.valid_name = a_child["valid_name"]
        ret.valid_authority = a_child["valid_authority"]
        ret.parent_name_usage_id = a_child["parentNameUsageID"]
        ret.kingdom = a_child["kingdom"]
        ret.phylum = a_child["phylum"]
        ret.class_ = a_child["class"]
        ret.order = a_child["order"]
        ret.family = a_child["family"]
        ret.genus = a_child["genus"]
        ret.citation = a_child["citation"]
        ret.lsid = a_child["lsid"]
        ret.is_marine = a_child["isMarine"]
        ret.is_brackish = a_child["isBrackish"]
        ret.is_freshwater = a_child["isFreshwater"]
        ret.is_terrestrial = a_child["isTerrestrial"]
        ret.is_extinct = a_child["isExtinct"]
        ret.match_type = a_child["match_type"]
        ret.modified = a_child["modified"]
        return ret

    def _do_refresh(self, starting_id: int):
        """
            Do the real job.
        """
        logger.info("Starting...")
        qry = self.session.query(WoRMS.aphia_id, WoRMS.all_fetched)
        self.existing_ids = {rec[0]: rec[1] for rec in qry.all()}
        logger.info("Existing: %d entries", len(self.existing_ids))

        self._add_children_of(starting_id)

        logger.info("Done.")

    def _add_children_of(self, starting_aphia_id: int):
        """
            Add in DB (recursively) the children of given taxon by its aphia_id.
        """
        if starting_aphia_id in self.existing_ids and self.existing_ids[starting_aphia_id]:
            children_qry = self.session.query(WoRMS.aphia_id)
            children_qry = children_qry.filter(WoRMS.parent_name_usage_id == starting_aphia_id)
            children_ids = set(only_res(children_qry.all()))
            logger.info("For %d DB says %s", starting_aphia_id, children_ids)
        else:
            # REST calls limit
            if self.nb_queries > 50000:
                return
            # It lloks like the parent is returned with its children
            children = WoRMSFinder.aphia_children_by_id(starting_aphia_id)
            self.nb_queries += 1
            children_ids = set()
            added = 0
            for a_child in children:
                to_add = self.json_to_ORM(a_child)
                children_ids.add(to_add.aphia_id)
                if to_add.aphia_id not in self.existing_ids:
                    logger.info("Adding to DB %d", to_add.aphia_id)
                    self.session.add(to_add)
                    self.existing_ids[to_add.aphia_id] = False
                    added += 1
            # if added > 0:
                    try:
                        self.session.commit()
                    except Exception as e:
                        logger.error("For parent %d and child %s : %s", starting_aphia_id, to_add.aphia_id,e)
                        self.session.rollback()
                        return
        # Recurse
        for a_child_id in children_ids:
            if a_child_id == starting_aphia_id:
                continue
            # if self.existing_ids[a_child_id]:
            #     continue
            self._add_children_of(a_child_id)
        # Signal done
        self.session.query(WoRMS).get(starting_aphia_id).all_fetched = True
        self.session.commit()

    # TODO: /AphiaRecordsByDate Lists all AphiaRecords (taxa) that have their last edit action (modified or added)
    #  during the specified period
    # Get max of dates in our DB as start of range
