# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Charset conversion waiting for all-to-UTF
#
def to_latin1_compat(a_str: str):
    if a_str is None:
        return a_str
    try:
        _str_lat1 = a_str.encode("latin-1")
    except UnicodeEncodeError:
        return str(a_str.encode("latin-1", errors='xmlcharrefreplace'))
    return a_str