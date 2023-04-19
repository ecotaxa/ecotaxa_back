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

from BO.Classification import ClassifIDListT, ClassifIDT
from BO.Rights import RightsBO
from BO.Taxonomy import TaxonomyBO
from BO.User import UserIDT
from DB.Project import ProjectTaxoStat
from DB.Taxonomy import Taxonomy
from DB.User import Role
from DB.WoRMs import WoRMS
from DB.helpers.Charset import to_latin1_compat
from DB.helpers.ORM import any_, Session, Alias
from DB.helpers.ORM import func, not_, or_, and_, text
from helpers.DynamicLogs import get_logger
from providers.EcoTaxoServer import EcoTaxoServerClient
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
        self.to_fetch: Deque[int] = deque()
        self.nb_queries = 0
        if max_requests is not None:
            self.max_queries = max_requests
        else:
            self.max_queries = self.MAX_QUERIES

    def log_file_path(self) -> str:
        self.temp_log = tempfile.NamedTemporaryFile(suffix=".log", delete=True).name
        return self.temp_log

    async def db_refresh(self, current_user_id: int) -> None:
        """
        Refresh the local taxonomy DB.
        """
        # Security check
        _user = RightsBO.user_has_role(
            self.ro_session, current_user_id, Role.APP_ADMINISTRATOR
        )
        await self._do_refresh()

    # noinspection PyPep8Naming
    @staticmethod
    def json_to_ORM(a_child: Dict) -> WoRMS:
        """
        Prepare a DB record from the JSON structure returned by WoRMS REST API.
        """
        to_lat1 = to_latin1_compat
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
        ret.valid_name = to_lat1(a_child["valid_name"])
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

    def _random_add_to_fetch(self, to_add: List[int]) -> None:
        random.shuffle(to_add)
        self.to_fetch.extend(to_add)

    async def _do_refresh(self) -> None:
        """
        Do the real job.
        """
        logger.info("Starting...")
        # Query all for fast existence testing
        qry = self.session.query(WoRMS.aphia_id, WoRMS.all_fetched)
        self.existing_ids = {aphia_id: all_fetched for aphia_id, all_fetched in qry}
        logger.info("Existing: %d entries", len(self.existing_ids))
        # What was not fetched needs to be
        self._random_add_to_fetch(
            [an_id for an_id in self.existing_ids if not self.existing_ids[an_id]]
        )
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
            except HTTPError as e:
                logger.warning("HTTP exception %s for %d.", str(e), id_to_fetch)
                continue
            # Report progress
            if len(children_ids) > 0:
                logger.info(
                    "Added to DB for %d: %s, %d queries done.",
                    id_to_fetch,
                    children_ids,
                    self.nb_queries,
                )
            else:
                logger.info(
                    "No child for {%d}, %d queries done.", id_to_fetch, self.nb_queries
                )
            # Add the children to the explore, in a random way
            self._random_add_to_fetch(list(children_ids))
        logger.info("Done, %d items remaining to fetch.", len(self.to_fetch))

    async def _add_children_of(self, parent_aphia_id: int) -> Set[int]:
        """
        Add in DB (recursively) the children of given taxon by its aphia_id.
        """
        # REST calls limit
        if self.nb_queries > self.max_queries:
            raise ResourceWarning("Not making more than %d queries", self.max_queries)
        # Note: It looks like the parent is returned with its children
        children, nb_queries = await WoRMSFinder.aphia_children_by_id(parent_aphia_id)
        self.nb_queries += nb_queries
        children_ids = set()
        added_children = []
        for a_child in children:
            to_add = self.json_to_ORM(a_child)
            to_add.all_fetched = False
            children_ids.add(to_add.aphia_id)
            if to_add.aphia_id in self.existing_ids:
                # TODO: Update
                pass
            else:
                self.session.add(to_add)
                added_children.append(to_add)
                self.existing_ids[to_add.aphia_id] = False
        # DB persist
        if len(children_ids) > 0:
            try:
                self.session.commit()
            except Exception as _e:
                self.session.rollback()
                return self._do_one_by_one(added_children)
        # Signal done
        worms_rec = self.session.query(WoRMS).get(parent_aphia_id)
        assert worms_rec is not None
        worms_rec.all_fetched = True
        self.session.commit()
        return children_ids

    async def _get_db_children(self, aphia_id: int):
        """
        Return the known list of children for this aphia_id
        """
        children_qry = self.session.query(WoRMS.aphia_id)
        children_qry = children_qry.filter(WoRMS.parent_name_usage_id == aphia_id)
        children_ids = set([an_id for an_id, in children_qry])
        return children_ids

    # TODO: /AphiaRecordsByDate Lists all AphiaRecords (taxa) that have their last edit action (modified or added)
    #  during the specified period
    # Get max of dates in our DB as start of range

    def matching(
        self, _current_user_id: int, params: Dict[str, Any]
    ) -> List[Tuple[Taxonomy, Optional[WoRMS]]]:
        """
        Return the list of matching entries b/w Taxonomy and WoRMS.
        """
        ret: List[Tuple[Taxonomy, Optional[WoRMS]]] = []
        taxo_ids_qry = self.session.query(ProjectTaxoStat.id).distinct()
        taxo_ids_qry = taxo_ids_qry.filter(ProjectTaxoStat.nbr > 0)
        used_taxo_ids = [an_id for an_id, in taxo_ids_qry]

        # No security check. TODO?
        case1 = "case1" in params
        """ Taxa with same name on both sides, Phylo in EcoTaxa and accepted in WoRMS """
        case2 = "case2" in params
        """ Taxa with same name on both sides, Morpho in EcoTaxa and accepted in WoRMS """
        case3 = "case3" in params
        """ Taxa with same name on both sides, Phylo in EcoTaxa and NOT accepted in WoRMS,
         and there is no equivalent accepted match """
        case31 = "case31" in params
        case4 = "case4" in params
        case5 = "case5" in params
        """ No match, phylo """
        case6 = "case6" in params

        if case1:
            res = self.strict_match(self.session, used_taxo_ids)
            # Format result
            for taxo, worms in res:
                ret.append((taxo, worms))
        elif case2:
            subqry = TaxonomyChangeService.strict_match_subquery(
                self.session, used_taxo_ids, phylo_or_morpho="M"
            )
            qry = self.session.query(Taxonomy, WoRMS)
            qry = qry.join(subqry, subqry.c.id == Taxonomy.id)
            qry = qry.join(WoRMS, subqry.c.aphia_id == WoRMS.aphia_id)
            logger.info("matching qry:%s", str(qry))
            res = qry.all()
            # Format result
            for taxo, worms in res:
                ret.append((taxo, worms))
        elif case3:
            # statuses = ["temporary name", "nomen nudum", "interim unpublished",
            #             "nomen dubium", "unaccepted", "taxon inquirendum",
            #             "accepted", "uncertain", "alternate representation"]
            # Match but the match/all matches are not accepted
            subqry = self.full_match_aggregated(used_taxo_ids)

            qry3 = self.session.query(Taxonomy, WoRMS)
            qry3 = qry3.join(subqry, subqry.c.id == Taxonomy.id)
            qry3 = qry3.join(WoRMS, subqry.c.aphia_id == WoRMS.aphia_id)
            qry3 = qry3.filter(
                not_(subqry.c.acc.op("@>")(text("ARRAY['accepted'::varchar]")))
            )
            qry3 = qry3.filter(WoRMS.valid_name != None)
            # Status filter for clarity
            # flt = statuses[4]
            # status_filt = text("ARRAY['%s'::varchar]" % flt)
            # qry3 = qry3.filter(subqry.c.acc.op('@>')(status_filt))
            logger.info("matching qry:%s", str(qry3))
            res3 = qry3.all()
            # Format result
            for taxo, worms in res3:
                ret.append((taxo, worms))
        elif case31:
            # Match but the match/all matches are not accepted
            subqry = self.full_match_aggregated(used_taxo_ids)

            qry31 = self.session.query(Taxonomy, WoRMS)
            qry31 = qry31.join(subqry, subqry.c.id == Taxonomy.id)
            qry31 = qry31.join(WoRMS, subqry.c.aphia_id == WoRMS.aphia_id)
            qry31 = qry31.filter(
                not_(subqry.c.acc.op("@>")(text("ARRAY['accepted'::varchar]")))
            )
            qry31 = qry31.filter(WoRMS.valid_name == None)
            logger.info("matching qry:%s", str(qry31))
            res31 = qry31.all()
            # Format result
            for taxo, worms in res31:
                ret.append((taxo, worms))
        elif case4:
            subqry = self.full_match_aggregated(used_taxo_ids)

            qry4 = self.session.query(Taxonomy, WoRMS)
            qry4 = qry4.join(subqry, subqry.c.id == Taxonomy.id)
            qry4 = qry4.join(WoRMS, subqry.c.aphia_id == WoRMS.aphia_id)
            qry4 = qry4.filter(subqry.c.cnt > 1)
            # Several accepted matches
            # subqry = self.session.query(Taxonomy.name, func.max(Taxonomy.id).label("id"), WoRMS.aphia_id)
            # subqry = subqry.join(WoRMS, TaxonomyChangeService.match_with_extension())
            # subqry = subqry.filter(Taxonomy.id == any_(used_taxo_ids))
            # subqry = subqry.filter(Taxonomy.taxotype == 'P')
            # subqry = subqry.filter(WoRMS.status == 'accepted')
            # # Group to compute multiple matches
            # subqry = subqry.group_by(Taxonomy.name, WoRMS.aphia_id)
            # subqry = subqry.having(or_(func.count(Taxonomy.name) > 1,
            #                            func.count(WoRMS.aphia_id) > 1))
            # subqry = subqry.subquery().alias("ids")
            #
            # qry4 = self.session.query(Taxonomy, WoRMS)
            # qry4 = qry4.join(subqry, subqry.c.id == Taxonomy.id)
            # qry4 = qry4.join(WoRMS, subqry.c.aphia_id == WoRMS.aphia_id)
            logger.info("matching qry:%s", str(qry4))
            res = qry4.all()
            # Format result
            for taxo, worms in res:
                ret.append((taxo, worms))
        elif case5:
            # No match, phylo
            subqry = TaxonomyChangeService.strict_match_subquery(
                self.session, used_taxo_ids, phylo_or_morpho=None
            )
            subqry2 = self.full_match_aggregated(used_taxo_ids)

            qry5 = self.session.query(Taxonomy)
            qry5 = qry5.filter(Taxonomy.id == any_(used_taxo_ids))
            qry5 = qry5.filter(Taxonomy.taxotype == "P")
            qry5 = qry5.filter(not_(Taxonomy.id.in_(self.session.query(subqry.c.id))))
            qry5 = qry5.filter(not_(Taxonomy.id.in_(self.session.query(subqry2.c.id))))
            logger.info("matching qry:%s", str(qry5))
            res5 = qry5.all()
            # Format result
            for taxo in res5:
                ret.append((taxo, None))
        elif case6:
            # No match, morpho
            subqry = TaxonomyChangeService.strict_match_subquery(
                self.session, used_taxo_ids, phylo_or_morpho=None
            )
            qry6 = self.session.query(Taxonomy)
            qry6 = qry6.filter(Taxonomy.id == any_(used_taxo_ids))
            qry6 = qry6.filter(Taxonomy.taxotype == "M")
            qry6 = qry6.filter(not_(Taxonomy.id.in_(self.session.query(subqry.c.id))))
            logger.info("matching qry:%s", str(qry6))
            res6 = qry6.all()
            # Format result
            for taxo in res6:
                ret.append((taxo, None))

        return ret

    def full_match_aggregated(self, used_taxo_ids) -> Alias:
        subqry = self.session.query(
            Taxonomy.id,
            WoRMS.aphia_id,
            func.array_agg(WoRMS.status)
            .over(partition_by=(Taxonomy.id, WoRMS.aphia_id))
            .label("acc"),
            func.count(Taxonomy.name).over(partition_by=(WoRMS.aphia_id)).label("cnt"),
        )
        subqry = subqry.join(WoRMS, TaxonomyChangeService.match_with_extension())
        subqry = subqry.filter(Taxonomy.id == any_(used_taxo_ids))
        subqry = subqry.filter(Taxonomy.taxotype == "P")
        ret = subqry.subquery().alias("ids")
        return ret

    @staticmethod
    def strict_match(
        session: Session, used_taxo_ids: ClassifIDListT
    ) -> List[Tuple[Taxonomy, WoRMS]]:
        """
        Candidate match until a better is found.
            We match Phylo types taxa on one side.
                using name <-> scientificname, case insensitive
            And a _single_ accepted taxon on the other.
        """
        subqry = TaxonomyChangeService.strict_match_subquery(
            session, used_taxo_ids, phylo_or_morpho="P"
        )

        qry = session.query(Taxonomy, WoRMS)
        qry = qry.join(subqry, subqry.c.id == Taxonomy.id)
        qry = qry.join(WoRMS, subqry.c.aphia_id == WoRMS.aphia_id)
        logger.info("matching qry:%s", str(qry))
        res = qry.all()
        return res

    @staticmethod
    def strict_match_subquery(session, used_taxo_ids, phylo_or_morpho: Optional[str]):
        subqry = session.query(
            Taxonomy.name, func.max(Taxonomy.id).label("id"), WoRMS.aphia_id
        )
        subqry = subqry.join(WoRMS, TaxonomyChangeService.match_with_extension())
        subqry = subqry.filter(Taxonomy.id == any_(used_taxo_ids))
        if phylo_or_morpho is not None:
            subqry = subqry.filter(Taxonomy.taxotype == text("'%s'" % phylo_or_morpho))
        subqry = subqry.filter(WoRMS.status == text("'accepted'"))
        # Group to exclude multiple matches
        subqry = subqry.group_by(Taxonomy.name, WoRMS.aphia_id)
        subqry = subqry.having(
            and_(func.count(Taxonomy.name) == 1, func.count(WoRMS.aphia_id) == 1)
        )
        subqry = subqry.subquery().alias("ids")
        return subqry

    @staticmethod
    def match_with_extension():
        # We also match if these are trailing on EcoTaxa side
        # ok_ext = [" X", " sp.", " X sp."]
        # ok_ext_txt = [text("'" + ext.lower() + "'") for ext in ok_ext]
        # match_name = [func.lower(WoRMS.scientificname)]
        # match_name += [func.concat(func.lower(WoRMS.scientificname), ext) for ext in ok_ext_txt]
        return or_(
            func.lower(Taxonomy.name) == func.lower(WoRMS.scientificname),
            and_(
                Taxonomy.name.like(text("'% X'")),
                func.lower(Taxonomy.name)
                == func.concat(func.lower(WoRMS.scientificname), text("' x'")),
            ),
            and_(
                Taxonomy.name.like(text("'% sp.'")),
                func.lower(Taxonomy.name)
                == func.concat(func.lower(WoRMS.scientificname), text("' sp.'")),
            ),
            and_(
                Taxonomy.name.like(text("'% X sp.'")),
                func.lower(Taxonomy.name)
                == func.concat(func.lower(WoRMS.scientificname), text("' x sp.'")),
            ),
        )

    def _do_one_by_one(self, children) -> Set[int]:
        """
        There was an error inserting children in bulk set. So do it one by one, and log
        the problem each time.
        """
        ret: Set[int] = set()
        for a_child in children:
            self.session.add(a_child)
            try:
                self.session.commit()
                ret.add(a_child.aphia_id)
            except Exception as e:
                self.session.rollback()
                logger.error("For child %s : %s", a_child, e)
        return ret

    async def check_id(self, current_user_id, aphia_id) -> str:
        """
        Check the given aphia_id, adjust the DB if needed.
        """
        # Security check
        _user = RightsBO.user_has_role(
            self.ro_session, current_user_id, Role.APP_ADMINISTRATOR
        )
        lineage = await WoRMSFinder.aphia_classif_by_id(aphia_id)
        # Nested struct, e.g. : {'AphiaID': 1, 'rank': 'Superdomain', 'scientificname': 'Biota', 'child':
        # {'AphiaID': 3, 'rank': 'Kingdom', 'scientificname': 'Plantae', 'child':
        # {'AphiaID': 368663, 'rank': 'Subkingdom', 'scientificname': 'Viridiplantae', 'child':
        # {'AphiaID': 536191, 'rank': 'Infrakingdom', 'scientificname': 'Streptophyta', 'child':
        # ...
        # }}}}}}}}}
        prev_level = None
        while lineage is not None:
            aphia_id_for_level = lineage["AphiaID"]
            db_entry = self.session.query(WoRMS).get(aphia_id_for_level)
            if db_entry is None:
                assert prev_level is not None
                prev_level.all_fetched = False
                self.session.commit()
                return "%d was not found, so parent %d was marked as incomplete" % (
                    aphia_id_for_level,
                    prev_level.aphia_id,
                )
            lineage = lineage["child"]
            prev_level = db_entry
        return "All OK"


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
        return ret

    def add_taxon(self, current_user_id: UserIDT, taxon_params: Dict) -> str:
        # Security barrier, user must be admin or manager in any project
        #                            creation_datetime: str, =
        _user = RightsBO.user_can_add_taxonomy(self.ro_session, current_user_id)
        # Amend params
        taxon_params["creation_datetime"] = datetime.datetime.utcnow().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        taxon_params["taxostatus"] = "N"
        ret = self.client.call("/settaxon/", taxon_params)
        return ret

    def push_stats(self) -> Any:
        """
        Push taxa usage statistics to EcoTaxoServer.
        """
        # Get data for update
        stats = TaxonomyBO.get_full_stats(self.ro_session)
        # Push to central
        params = {"data": json.dumps(stats)}
        ret = self.client.call("/setstat/", params)
        if "msg" in ret:
            TaxonomyBO.update_tree_status(self.session)
        return ret

    # The columns received from EcoTaxoServer which can update the local tree
    UpdatableCols: Final = [
        "parent_id",
        "name",
        "taxotype",
        "taxostatus",
        "id_source",
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
        updates = self.client.call(
            "/gettaxon/", {"filtertype": "since", "startdate": max_updated_str}
        )
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

        to_rename: Dict[ClassifIDT, ClassifIDT] = {}

        for a_json_taxon in updates:
            # Convert non-str fields
            json_taxon_id = int(a_json_taxon["id"])
            lastupdate_datetime = datetime.datetime.strptime(
                a_json_taxon["lastupdate_datetime"], "%Y-%m-%d %H:%M:%S"
            )
            # Store rename intentions
            if a_json_taxon["rename_to"]:
                to_rename[json_taxon_id] = int(a_json_taxon["rename_to"])
            # Read taxon from DB
            taxon = self.session.query(Taxonomy).get(json_taxon_id)
            if taxon is not None:
                # The taxon is already present
                if taxon.lastupdate_datetime == lastupdate_datetime:
                    continue  # already up to date
                nbr_updates += 1
            else:
                # The taxon is not present, create it
                nbr_inserts += 1
                taxon = Taxonomy()
                taxon.id = json_taxon_id
                self.session.add(taxon)
            # We have a taxon, either brand new or already there, update it
            for a_col in self.UpdatableCols:
                setattr(taxon, a_col, a_json_taxon[a_col])
            taxon.lastupdate_datetime = lastupdate_datetime
            self.session.commit()
        # Manage rename_to
        if len(to_rename) > 0:
            TaxonomyBO.do_renames(self.session, to_rename)

        # if gvp('updatestat') == 'Y':
        #     msg = DoSyncStatUpdate()
        #     flash("Taxon statistics update : " + msg, "success" if msg == 'ok' else 'error')

        return {"inserts": nbr_inserts, "updates": nbr_updates, "error": None}
