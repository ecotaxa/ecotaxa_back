# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, Optional, Tuple

import httpx

from db.Taxonomy import Taxonomy
from framework.Service import Service


class WoRMSFinder(Service):
    """
        A service for finding in WoRMS service the equivalent of a given entry in Taxonomy.
    """
    client = httpx.AsyncClient(base_url="http://www.marinespecies.org")

    taxo_cache: Dict[int, Taxonomy] = {}

    def __init__(self, taxo_id: int):
        super().__init__()
        #
        self.id_to_find: int = taxo_id

    def get_taxonomy(self, our_id: int) -> Optional[Taxonomy]:
        from_cache = self.taxo_cache.get(our_id)
        if from_cache:
            return from_cache
        ret = self.session.query(Taxonomy).filter_by(id=our_id).first()
        if ret:
            self.taxo_cache[our_id] = ret
        return ret

    async def run(self) -> Tuple[int, str, str]:
        """
            Do the real job using injected parameters.
            :return:
        """
        taxon: Taxonomy = self.get_taxonomy(self.id_to_find)
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
            return "%s > %s" % (self.get_lineage(parent), taxon.name)
