# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Managing (i.e. not for end-user) services around taxonomy tree.
#
import datetime
import json
from typing import Dict, List, Any, Final

from BO.Classification import ClassifIDT
from BO.Rights import RightsBO
from BO.Taxonomy import TaxonomyBO
from DB.Taxonomy import Taxonomy
from DB.User import UserIDT
from DB.helpers.ORM import Session
from helpers import DateTime
from helpers.AppConfig import Config
from helpers.DynamicLogs import get_logger
from providers.EcoTaxoServer import EcoTaxoServerClient
from .helpers.Service import Service

logger = get_logger(__name__)


class CentralTaxonomyService(Service):
    """
    Communication with EcoTaxoServer, for various purposes.
    """

    def __init__(self) -> None:
        super().__init__()
        self.client = self.build_client(self.config)

    @staticmethod
    def build_client(config: Config) -> EcoTaxoServerClient:
        url = config.get_taxoserver_url()
        my_id = config.get_taxoserver_instance_id()
        my_key = config.get_taxoserver_shared_secret()
        return EcoTaxoServerClient(url, my_id, my_key)

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
        ret = self.client.call("/wormstaxon/%s" % name, {}, "get")
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
        return self._push_stats(self.ro_session, self.session, self.client)

    @staticmethod
    def push_stats_for(ro_session: Session, session: Session, config: Config) -> Any:
        return CentralTaxonomyService._push_stats(
            ro_session, session, CentralTaxonomyService.build_client(config)
        )

    @staticmethod
    def _push_stats(
        ro_session: Session, session: Session, client: EcoTaxoServerClient
    ) -> Any:
        # Get data for update
        stats = TaxonomyBO.get_full_stats(ro_session)
        # Push to central
        params = {"data": json.dumps(stats)}
        ret = client.call("/setstat/", params)
        retstat = ret.json()
        if "msg" in retstat:
            TaxonomyBO.update_tree_status(session)
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
        return self._pull_updates(self.session, self.client)

    @staticmethod
    def pull_updates_for(session: Session, config: Config) -> Dict[str, Any]:
        return CentralTaxonomyService._pull_updates(
            session, CentralTaxonomyService.build_client(config)
        )

    @classmethod
    def _pull_updates(
        cls, session: Session, client: EcoTaxoServerClient
    ) -> Dict[str, Any]:
        # Get latest update date for local taxonomy
        max_updated = TaxonomyBO.get_latest_update(session)
        if max_updated is None:
            max_updated = datetime.datetime(2000, 1, 1)
        # Ask central what changed since
        max_updated_str = max_updated.strftime("%Y-%m-%d %H:%M:%S")
        ret = client.call(
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
            taxon = session.get(Taxonomy, json_taxon_id)
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
                session.add(taxon)
            # We have a taxon, either brand new or already there, update it
            for a_col in cls.UpdatableCols:
                setattr(taxon, a_col, a_json_taxon[a_col])
            taxon.lastupdate_datetime = lastupdate_datetime
            # TODO: Below is mandatory as we alter trigger for fast deletion
            # But we lose, in case of failure, the facility to re-sync, which is based on last
            # updated date of taxonomy entries, nothing for deletes here.
            session.commit()
        if len(to_delete) > 0:
            TaxonomyBO.do_deletes(session, to_delete)
            session.commit()

        # if gvp('updatestat') == 'Y':
        #     msg = DoSyncStatUpdate()
        #     flash("Taxon statistics update : " + msg, "success" if msg == 'ok' else 'error')

        return {"inserts": nbr_inserts, "updates": nbr_updates, "error": None}
