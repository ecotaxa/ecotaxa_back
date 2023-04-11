# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Charset conversion waiting for all-to-UTF
#
import html


def to_latin1_compat(a_str: str):
    if a_str is None:
        return a_str
    try:
        _str_lat1 = a_str.encode("latin-1")
    except UnicodeEncodeError:
        ret = a_str.encode("latin-1", errors="xmlcharrefreplace")
        return ret
    return a_str


def from_xmlchar(a_str: str):
    """Convert back if a string was stored with latin1 due to no-utf8-in-DB"""
    if "&#" in a_str:
        return html.unescape(a_str)
    return a_str
