# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from db.Connection import Connection, check_sqlalchemy_version
from link import read_config, read_link


class BaseService(object):
    """
        A service, i.e. a stateless object which lives only for the time it does its job.
    """


class Service(BaseService):
    """
        A service for EcoTaxa. Supplies common useful features like a DB session and filesystem conventions.
    """

    def __init__(self):
        check_sqlalchemy_version()
        config = read_config()
        conn = Connection(host=config['DB_HOST'], port=config['DB_PORT'], db=config['DB_DATABASE'],
                          user=config['DB_USER'], password=config['DB_PASSWORD'])
        self.session: Session = conn.sess
        self.config = config
        self.link_src = read_link()[0]
