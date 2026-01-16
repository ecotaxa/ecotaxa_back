# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Managing (i.e. not for end-user) services around taxonomy tree.
#
import datetime
import json
import random
import tempfile
from collections import deque
from typing import Dict, Set, List, Tuple, Any, Optional, Final, Deque

from httpx import ReadTimeout, HTTPError

from BO.Classification import ClassifIDT
from BO.Rights import RightsBO
from BO.Taxonomy import TaxonomyBO
from BO.User import UserIDT
from DB.Taxonomy import Taxonomy
from DB.User import User
from helpers import DateTime
from helpers.DynamicLogs import get_logger
from providers.EcoTaxoServer import EcoTaxoServerClient
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
        self.to_fetch: Deque[int] = deque()
        self.nb_queries = 0
        if max_requests is not None:
            self.max_queries = max_requests
        else:
            self.max_queries = self.MAX_QUERIES

    def log_file_path(self) -> str:
        self.temp_log = tempfile.NamedTemporaryFile(suffix=".log", delete=True).name
        return self.temp_log


class CentralTaxonomyService(Service):
    """
    Communication with EcoTaxoServer, for various purposes.
    """

    # Configuration keys
    TAXOSERVER_URL_KEY = "TAXOSERVER_URL"
    TAXOSERVER_MY_ID = "TAXOSERVER_INSTANCE_ID"
    TAXOSERVER_MY_SECRET_KEY = "TAXOSERVER_SHARED_SECRET"

    def __init__(self) -> None:
        super().__init__()
        url = self.config.get_cnf(self.TAXOSERVER_URL_KEY)
        assert url is not None
        my_id = self.config.get_cnf(self.TAXOSERVER_MY_ID)
        assert my_id is not None
        my_key = self.config.get_cnf(self.TAXOSERVER_MY_SECRET_KEY)
        assert my_key is not None
        self.client = EcoTaxoServerClient(url, my_id, my_key)

    def get_taxon_by_id(self, taxon_id: int) -> str:
        """Read all taxon data from EcoTaxoServer"""
        ret = self.client.call("/gettaxon/", {"filtertype": "id", "id": taxon_id})
        return ret.json()

    def add_taxon(self, current_user_id: UserIDT, taxon_params: Dict) -> Any:
        # Security barrier, user must be admin or manager in any project
        #                            creation_datetime: str, =
        _user = RightsBO.user_can_add_taxonomy(self.ro_session, current_user_id)
        # Amend params
        taxon_params["creation_datetime"] = DateTime.now_time().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        taxon_params["taxostatus"] = "N"
        ret = self.client.call("/settaxon/", taxon_params)
        return ret.json()

    def search_worms_name(self, name: str) -> List[Dict]:
        ret = self.client.call("/wormstaxon/%s" % name, {},'get')
        ret = ret.json()
        return ret

    def add_worms_taxon(
        self,
        aphia_id: int,
        current_user_id: UserIDT,
    ) -> Any:
        current_user = RightsBO.user_can_add_taxonomy(self.ro_session, current_user_id)
        taxon = {"aphia_id": aphia_id, "creator_email": current_user.email}
        ret = self.client.call("/addwormstaxon/", taxon)
        return ret.json()

    def push_stats(self) -> Any:
        """
        Push taxa usage statistics to EcoTaxoServer.
        """
        # Get data for update
        stats = TaxonomyBO.get_full_stats(self.ro_session)
        # Push to central
        params = {"data": json.dumps(stats)}
        ret = self.client.call("/setstat/", params)
        retstat = ret.json()
        if "msg" in retstat:
            TaxonomyBO.update_tree_status(self.session)
        return retstat

    # The columns received from EcoTaxoServer which can update the local tree
    UpdatableCols: Final = [
        "parent_id",
        "name",
        "taxotype",
        "taxostatus",
        "aphia_id",
        "rank",
        "id_instance",
        "rename_to",
        "display_name",
        "source_desc",
        "source_url",
        "creation_datetime",
        "creator_email",
    ]

    def pull_updates(self) -> Dict[str, Any]:
        """
        Pull taxa changes from EcoTaxoServer
        """
        # Get latest update date for local taxonomy
        max_updated = TaxonomyBO.get_latest_update(self.session)
        if max_updated is None:
            max_updated = datetime.datetime(2000, 1, 1)
        # Ask central what changed since
        max_updated_str = max_updated.strftime("%Y-%m-%d %H:%M:%S")
        ret = self.client.call(
            "/gettaxon/", {"filtertype": "since", "startdate": max_updated_str}
        )
        updates = ret.json()
        # Note: The query on EcoTaxoServer uses >=, so the last updated taxon is always returned.
        if "msg" in updates:
            return {"error": updates["msg"]}

        # Example response:  [{'creation_datetime': '2021-08-20 09:09:39',
        # 'creator_email': 'laurent.salinas@laposte.net', 'display_name': 'Devtest',
        # 'id': 93817, 'id_instance': 1, 'id_source': '',
        # 'lastupdate_datetime': '2021-08-20 09:09:40',
        # 'name': 'Devtest', 'parent_id': 93550, 'rename_to': None,
        # 'source_desc': '', 'source_url': 'http://www.google.fr/', 'taxostatus': 'N', 'taxotype': 'P'}]
        nbr_rows = len(updates)
        nbr_updates = nbr_inserts = 0

        to_delete: List[ClassifIDT] = []

        for a_json_taxon in updates:
            # Convert non-str fields
            json_taxon_id = int(a_json_taxon["id"])
            lastupdate_datetime = datetime.datetime.strptime(
                a_json_taxon["lastupdate_datetime"], "%Y-%m-%d %H:%M:%S"
            )
            must_delete = a_json_taxon["taxostatus"] == "X"
            # Read taxon from DB
            taxon = self.session.query(Taxonomy).get(json_taxon_id)
            if taxon is not None:
                if must_delete:
                    to_delete.append(json_taxon_id)
                    continue
                # The taxon is already present
                if taxon.lastupdate_datetime == lastupdate_datetime:
                    continue  # already up to date
                nbr_updates += 1
            else:
                if must_delete:
                    continue  # Should not happen if timestamps are OK
                # The taxon is not present, create it
                nbr_inserts += 1
                taxon = Taxonomy()
                taxon.id = json_taxon_id
                self.session.add(taxon)
            # We have a taxon, either brand new or already there, update it
            for a_col in self.UpdatableCols:
                setattr(taxon, a_col, a_json_taxon[a_col])
            taxon.lastupdate_datetime = lastupdate_datetime
            # TODO: Below is mandatory as we alter trigger for fast deletion
            # But we lose, in case of failure, the facility to re-sync, which is based on last
            # updated date of taxonomy entries, nothing for deletes here.
            self.session.commit()
        if len(to_delete) > 0:
            TaxonomyBO.do_deletes(self.session, to_delete)
            self.session.commit()

        # if gvp('updatestat') == 'Y':
        #     msg = DoSyncStatUpdate()
        #     flash("Taxon statistics update : " + msg, "success" if msg == 'ok' else 'error')

        return {"inserts": nbr_inserts, "updates": nbr_updates, "error": None}
