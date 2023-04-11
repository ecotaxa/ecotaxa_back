# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from os.path import join
from pathlib import Path

# noinspection PyPackageRequirements
import link

from .processes import SyncSubProcess


class LegacyProcess(object):
    """
    A process in legacy version of EcoTaxa
    """

    def __init__(self):
        self.src_path, self.venv_path = link.read_link()
        # TODO: On Windows?
        self.venv_py = join(self.venv_path, "bin", "python")


class Manage(LegacyProcess):
    """
    Manage.py commands
    """

    def run_create_db(self):
        manage_py = join(self.src_path, "manage.py")
        assert Path(manage_py).exists()
        # Use current python
        cmd = [self.venv_py]
        cmd += [manage_py, "CreateDB", "-U"]
        # Launch the command
        # NOTE: A confirmation is asked (prompted)
        SyncSubProcess(cmd, cwd=self.src_path)
