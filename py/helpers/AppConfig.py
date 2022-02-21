# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Application configuration, in a file, pointed at with an env. variable
#

import configparser
import os
from pathlib import Path
from typing import Optional

# Env. variable
ENV_KEY = "APP_CONFIG"


class Config(object):
    """
        The application configuration
    """

    def __init__(self):
        if ENV_KEY in os.environ:
            config_file = Path(os.environ[ENV_KEY])
        else:
            # For dev mode and tests
            config_file = "config.ini"
        # Config needs to be in an ini-like format
        config_parser = configparser.ConfigParser()
        config_parser.read(config_file)
        self.parser = config_parser["conf"]

    def vault_dir(self) -> str:
        return self.parser.get("VAULT_DIR")

    def jobs_dir(self) -> str:
        return self.parser.get("JOBS_DIR")

    def common_folder(self) -> str:
        return self.parser.get("SERVERLOADAREA")

    def export_folder(self) -> str:
        return self.parser.get("FTPEXPORTAREA")

    def secret_key(self) -> str:
        return self.parser.get("SECRET_KEY")

    def get_cnf(self, key: str, default: Optional[str] = None):
        return self.parser.get(key, default)

    def list_cnf(self):
        return self.parser.keys()
