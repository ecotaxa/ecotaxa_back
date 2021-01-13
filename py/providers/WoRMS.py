# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Wrapper for using http://www.marinespecies.org/index.php and its REST services
#
from typing import Dict, Tuple, List, Any

import httpx
import requests

from helpers.Asyncio import async_sleep


# noinspection PyPackageRequirements,PyProtectedMember


class WoRMSFinder(object):
    """
        A utility for finding in WoRMS service the equivalent of a given entry in Taxonomy.
    """
    BASE_URL = "http://www.marinespecies.org"
    client = httpx.AsyncClient(base_url=BASE_URL, timeout=5)
    the_session = None

    WoRMS_AphiaRecordByName = "/rest/AphiaRecordsByName/%s?marine_only=true"

    @classmethod
    def aphia_records_by_name_sync(cls, name: str) -> List[Dict]:  # pragma:nocover
        ret: List[Dict] = []
        session = cls.get_session()
        req = cls.WoRMS_AphiaRecordByName % name
        response = session.get(cls.BASE_URL + req)
        if not response.ok:
            cls.invalidate_session()
        else:
            if response.status_code == 204:  # No content
                pass
            else:
                ret = response.json()
        return ret

    WoRMS_URL_ClassifByAphia = "/rest/AphiaClassificationByAphiaID/%d"

    @classmethod
    async def aphia_classif_by_id(cls, aphia_id: int) -> Any:  # pragma:nocover
        req = cls.WoRMS_URL_ClassifByAphia % aphia_id
        response = await cls.client.get(req)
        if response.is_error:
            ret = ""
        else:
            ret = response.json()
        return ret

    WoRMS_URL_ClassifChildrenByAphia = "/rest/AphiaChildrenByAphiaID/%d?marine_only=false&offset=%d"

    CHUNK_SIZE = 50

    @classmethod
    async def aphia_children_by_id(cls, aphia_id: int, page=0) -> Tuple[List[Dict], int]:  # pragma:nocover
        # Throttle to 1 req/s
        await async_sleep(1)
        res: List[Dict] = []
        chunk_num = page * cls.CHUNK_SIZE + 1
        req = cls.WoRMS_URL_ClassifChildrenByAphia % (aphia_id, chunk_num)
        nb_queries = 1
        # try:
        response = await cls.client.get(cls.BASE_URL + req)
        # Seen: httpcore._exceptions.ProtocolError: can't handle event type ConnectionClosed
        # when role=SERVER and state=SEND_RESPONSE
        # except ProtocolError as e:
        #     raise HTTP_X_Error("%s trying %s" % (e, req), request=req)
        if response.status_code == 204:
            # No content
            pass
        elif response.status_code == 200:
            res = response.json()
            if len(res) == cls.CHUNK_SIZE:
                next_page, cont_queries = await cls.aphia_children_by_id(aphia_id, page + 1)
                res.extend(next_page)
                nb_queries += cont_queries
        # else:
        #     raise HTTP_X_Error("%d trying %s" % (response.status_code, req), request=req)
        return res, nb_queries

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
