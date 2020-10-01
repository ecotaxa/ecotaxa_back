# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Wrapper for using http://www.marinespecies.org/index.php and its REST services
#
from typing import Dict, Optional, Tuple, List

import httpx
import requests

from DB import Session, Taxonomy


class WoRMSFinder(object):
    """
        A utility for finding in WoRMS service the equivalent of a given entry in Taxonomy.
    """
    BASE_URL = "http://www.marinespecies.org"
    client = httpx.AsyncClient(base_url=BASE_URL)

    taxo_cache: Dict[int, Taxonomy] = {}

    def __init__(self, session: Session, taxo_id: int):
        self.session = session
        self.id_to_find: int = taxo_id

    def get_taxonomy(self, our_id: int) -> Optional[Taxonomy]:
        from_cache = self.taxo_cache.get(our_id)
        if from_cache:
            return from_cache
        ret = self.session.query(Taxonomy).get(our_id)
        if ret:
            self.taxo_cache[our_id] = ret
        return ret

    async def run(self) -> Tuple[int, str, str]:
        """
            Do the real job using injected parameters.
            :return:
        """
        taxon = self.get_taxonomy(self.id_to_find)
        if taxon is None:
            return -1, "", ""
        our_lineage = self.get_lineage(taxon)
        ret = await self.aphia_id_by_name(taxon.name)
        if ret < 0:
            return ret, our_lineage, ""
        worms_lineage = await self.aphia_classif_by_id(ret)
        return 0, our_lineage, worms_lineage

    WoRMS_AphiaByName = "/rest/AphiaIDByName/%s?marine_only=true"

    @classmethod
    async def aphia_id_by_name(cls, name: str) -> int:
        req = cls.WoRMS_AphiaByName % name
        response = await cls.client.get(req)
        if response.is_error:
            print(name, "-> (ERR)", response)
            ret = -2
        else:
            ret = response.json()
        return ret

    WoRMS_AphiaRecordByName = "/rest/AphiaRecordsByName/%s?marine_only=true"

    the_session = None

    @classmethod
    def aphia_records_by_name_sync(cls, name: str) -> List[Dict]:
        ret: List[Dict] = []
        session = cls.the_session
        if session is None:
            session = requests.Session()
            cls.the_session = session
        req = cls.WoRMS_AphiaRecordByName % name
        response = session.get(cls.BASE_URL + req)
        if not response.ok:
            cls.the_session = None
        else:
            if response.status_code == 204:  # No content
                pass
            else:
                ret = response.json()
        return ret

    WoRMS_URL_ClassifByAphia = "/rest/AphiaClassificationByAphiaID/%d"

    @classmethod
    async def aphia_classif_by_id(cls, aphia_id: int) -> str:
        req = cls.WoRMS_URL_ClassifByAphia % aphia_id
        response = await cls.client.get(req)
        if response.is_error:
            ret = ""
        else:
            ret = cls.store_and_parse(response.json())
        return ret

    @classmethod
    def store_and_parse(cls, aphia_record) -> str:
        """
            E.g.: {"AphiaID":1,"rank":"Superdomain","scientificname":"Biota",
                     "child":{"AphiaID":2,"rank":"Kingdom","scientificname":"Animalia",...
        :param aphia_record:
        :return:
        """
        ret = []
        rec = aphia_record
        while rec is not None:
            # TODO: Store association AphiaID <-> scientificname somewhere e.g. in DB.
            ret.append(rec["scientificname"])
            rec = rec.get("child")
        return " > ".join(ret)

    def get_lineage(self, taxon: Taxonomy) -> str:
        """
            Rebuild lineage string for the given taxon.
        :param taxon: 
        :return: 
        """
        if taxon.parent_id is None:
            return taxon.name
        else:
            parent = self.get_taxonomy(taxon.parent_id)
            assert parent is not None
            return "%s > %s" % (self.get_lineage(parent), taxon.name)

    WoRMS_URL_ClassifChildrenByAphia = "/rest/AphiaChildrenByAphiaID/%d?offset=%d"

    CHUNK_SIZE = 50

    @classmethod
    async def aphia_children_by_id(cls, aphia_id: int, page=0) -> List[Dict]:
        ret: List[Dict] = []
        chunk_num = page * cls.CHUNK_SIZE + 1
        req = cls.WoRMS_URL_ClassifChildrenByAphia % (aphia_id, chunk_num)
        response = await cls.client.get(cls.BASE_URL + req)
        if response.status_code == 204:
            # No  content
            pass
        elif response.status_code == 200:
            ret = response.json()
            if len(ret) == cls.CHUNK_SIZE:
                next_page = await cls.aphia_children_by_id(aphia_id, page+1)
                ret.extend(next_page)
        else:
            raise Exception("Unexpected %s" % response)
        return ret

    @classmethod
    def get_session(cls):
        """ Cache the session to marinespecies.org, for speed and saving resources """
        session = cls.the_session
        if session is None:
            session = requests.Session()
            cls.the_session = session
        return cls.the_session

    @classmethod
    def invalidate_session(cls):
        cls.the_session = None
