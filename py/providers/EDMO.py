# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# https://edmo.seadatanet.org/ European Directory of Marine Organisations, via its SPARQL endpoint
#

from typing import List, NamedTuple, Optional, Dict, Any

import requests

from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class EDMOOrganization(NamedTuple):
    code: int
    name: str


class EDMOFetcher(object):
    """
    A utility for finding organizations, i.e. their EDMO code and official name, in EDMO
    """

    SPARQL_URL = "https://edmo.seadatanet.org/sparql/sparql"
    REPORT_URL = "https://edmo.seadatanet.org/report/"
    # EDMO answers 404 to the default python-requests User-Agent
    USER_AGENT = "EcoTaxa"
    TIMEOUT = 5
    MAX_RESULTS = 10
    MAX_SEARCH_RESULTS = 20
    MIN_SEARCH_LEN = 3
    the_session = None

    PREFIXES = """PREFIX org: <http://www.w3.org/ns/org#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""

    @classmethod
    def find_by_name(cls, name: str) -> List[EDMOOrganization]:
        """Organizations with exactly this name, case-insensitive"""
        name = name.strip()
        if name == "":
            return []
        sparql = cls.PREFIXES + (
            "SELECT ?code ?name WHERE {"
            " ?org a org:Organization ; org:name ?name ; skos:notation ?code ."
            " FILTER(lcase(str(?name)) = lcase(%s)) } LIMIT %d"
            % (cls._literal(name), cls.MAX_RESULTS)
        )
        return cls._organizations(cls._query(sparql))

    @classmethod
    def search(cls, name_part: str) -> List[EDMOOrganization]:
        """Organizations with a name containing name_part, case-insensitive, for autocompletion"""
        name_part = name_part.strip()
        if len(name_part) < cls.MIN_SEARCH_LEN:
            return []
        sparql = cls.PREFIXES + (
            "SELECT ?code ?name WHERE {"
            " ?org a org:Organization ; org:name ?name ; skos:notation ?code ."
            " FILTER(contains(lcase(str(?name)), lcase(%s))) } ORDER BY ?name LIMIT %d"
            % (cls._literal(name_part), cls.MAX_SEARCH_RESULTS)
        )
        return cls._organizations(cls._query(sparql))

    @classmethod
    def get_by_code(cls, code: int) -> Optional[EDMOOrganization]:
        """The organization with this EDMO code, if any"""
        sparql = cls.PREFIXES + (
            "SELECT ?code ?name WHERE {"
            " <%s%d> a org:Organization ; org:name ?name ; skos:notation ?code . } LIMIT 1"
            % (cls.REPORT_URL, int(code))
        )
        found = cls._organizations(cls._query(sparql))
        return found[0] if len(found) > 0 else None

    @staticmethod
    def _literal(val: str) -> str:
        """A SPARQL string literal, escaped"""
        for char, escaped in (
            ("\\", "\\\\"),
            ('"', '\\"'),
            ("\n", "\\n"),
            ("\r", "\\r"),
            ("\t", "\\t"),
        ):
            val = val.replace(char, escaped)
        return '"' + val + '"'

    @staticmethod
    def _organizations(bindings: List[Dict[str, Any]]) -> List[EDMOOrganization]:
        ret = []
        for a_binding in bindings:
            try:
                code = int(a_binding["code"]["value"])
                name = a_binding["name"]["value"].strip()
            except (KeyError, ValueError, TypeError, AttributeError):
                continue
            ret.append(EDMOOrganization(code, name))
        return ret

    @classmethod
    def _query(cls, sparql: str) -> List[Dict[str, Any]]:
        """Run the query, EDMO being unavailable must not prevent the caller from working"""
        session = cls.get_session()
        try:
            response = session.get(
                cls.SPARQL_URL,
                params={"query": sparql},
                headers={
                    "Accept": "application/sparql-results+json",
                    "User-Agent": cls.USER_AGENT,
                },
                timeout=cls.TIMEOUT,
            )
            if not response.ok:
                logger.warning("EDMO query failed with status %d", response.status_code)
                cls.invalidate_session()
                return []
            if response.status_code == 204:  # No content
                return []
            return response.json()["results"]["bindings"]
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            logger.warning("EDMO query failed: %s", e)
            cls.invalidate_session()
            return []

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
