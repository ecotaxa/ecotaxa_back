# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2024  Picheral, Colin, Irisson (UPMC-CNRS)
#
# https://eds.ukri.org/ NERC Vocabulary Server
#

import requests


class NERCFetcher(object):
    """
    A utility for getting extra info from a controlled vocabulary URL
    """

    BASE_URL = "http://vocab.nerc.ac.uk"
    the_session = None

    JSON_REQ = "?_profile=nvs&_mediatype=application/ld+json"

    @classmethod
    def get_preferred_name(cls, vocab_url: str) -> str:
        assert vocab_url.startswith(cls.BASE_URL)
        session = cls.get_session()
        response = session.get(vocab_url + cls.JSON_REQ, timeout=5)
        if not response.ok:
            cls.invalidate_session()
            return ""
        else:
            if response.status_code == 204:  # No content
                return ""
            else:
                ret = response.json()
        return ret["skos:prefLabel"]["@value"]

    @classmethod
    def get_session(cls):
        """Cache the session to base site, for speed and saving resources"""
        session = cls.the_session
        if session is None:
            session = requests.Session()
            cls.the_session = session
        return cls.the_session

    @classmethod
    def invalidate_session(cls):
        cls.the_session = None
