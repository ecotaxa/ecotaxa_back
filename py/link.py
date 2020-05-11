# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

# Link with legacy

import configparser
from os import path
from os.path import abspath, join

# Base on current file path so the script can be launched from anywhere
INI_DIR = path.join(path.dirname(__file__), "..")
INI_FILE = path.join(INI_DIR, "link.ini")


def read_link():
    config = configparser.ConfigParser()
    config.read(INI_FILE)
    # Make relative (to running process) paths
    conf = config['PATHS']
    abs_conf = {}
    for k in conf:
        abs_path = abspath(path.join(INI_DIR, conf[k]))
        assert path.exists(abs_path), "%s does not exist for key %s" % (abs_path, k)
        abs_conf[k] = abs_path
    return abs_conf['spagh_src']


def read_config():
    legacy_src = read_link()
    # We have to cook a pseudo-config as configparser needs an ini-like section
    config_file = join(legacy_src, "appli", "config.cfg")
    config_string = "[conf]\n" + open(config_file).read()
    config_string = config_string.replace('"', '')
    config_parser = configparser.ConfigParser()
    config_parser.read_string(config_string)
    return config_parser["conf"]
