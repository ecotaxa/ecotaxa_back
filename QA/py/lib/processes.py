# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import subprocess


class SyncSubProcess(object):
    """
    A process for which we wait for termination.
    """

    def __init__(self, args, env=None, cwd=None, out_file=None):
        if out_file:
            out_file = open(out_file, "w")
        self.pid = subprocess.call(
            args=args,
            env=env,
            shell=False,
            cwd=cwd,
            timeout=20,
            universal_newlines=True,
            stdout=out_file,
            stderr=subprocess.STDOUT,
        )
