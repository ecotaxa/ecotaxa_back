# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy.orm import Session

from db.Connection import Connection, check_sqlalchemy_version
from link import read_config, read_link


class Service(object):
    """
    A service, i.e. a stateless object which lives only for the time it does its job.
    """

    def __init__(self):
        check_sqlalchemy_version()
        config = read_config()
        conn = Connection(host=config['DB_HOST'], user=config['DB_USER'], password=config['DB_PASSWORD']
                          , db=config['DB_DATABASE'])
        self.session: Session = conn.sess
        self.config = config
        self.link_src = read_link()[0]
