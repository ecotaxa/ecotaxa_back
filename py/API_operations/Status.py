# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path

from .helpers.Service import Service


class StatusService(Service):
    """
        A utility service for ensuring the sanity of environment/config.
        Useful inside a docker container.
    """

    def __init__(self):
        super().__init__()

    # TODO: Use const from elsewhere
    PATHS_IN_CONF = ['SERVERLOADAREA', 'FTPEXPORTAREA', 'MODELSAREA']

    def run(self):
        """
            Produce the answer.
        """
        ret = ["Config dump:"]
        for k in self.config.list_cnf():
            v = self.config.get_cnf(k)
            if 'secret' in k.lower() or 'salt' in k.lower() or 'password' in k.lower():
                v = "*************"
            ret.append("  %s: %s" % (k, v))
        ret.append("Paths:")
        for pk in self.PATHS_IN_CONF:
            try:
                path_str = self.config.get_cnf(pk)
            except KeyError:
                path_str = None
            if path_str is None:
                ret.append("  %s not found" % pk)
                continue
            path = Path(path_str.strip("'"))
            if path.exists():
                status = "OK"
            else:
                status = "*** KO ***"
            ret.append("  %s (from %s): %s" % (path, pk, status))
        ret.append("")
        return "\n".join(ret)
