# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from pathlib import Path

# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from db.Connection import Connection, check_sqlalchemy_version
from link import read_config, read_link


class BaseService(object):
    """
        A service, i.e. a stateless object which lives only for the time it does its job.
    """


def _turn_localhost_for_docker(host: str, port: str):
    """ Turn localhost to the address as seen from inside the container
        For win & mac0s there is a solution, environment var host.docker.internal
         but https://github.com/docker/for-linux/issues/264
    """
    if host == "localhost":
        # If we can direct connect via socket then do it
        socket_path = Path("/var/run/postgresql/.s.PGSQL.%s" % port)
        if socket_path.is_socket():
            # Will turn to a socket connection, i.e. no network interface needed
            return ""
    return host


class Service(BaseService):
    """
        A service for EcoTaxa. Supplies common useful features like a DB session and filesystem conventions.
    """

    def __init__(self):
        check_sqlalchemy_version()
        config = read_config()
        port = config['DB_PORT']
        host = _turn_localhost_for_docker(config['DB_HOST'], port)
        conn = Connection(host=host, port=port, db=config['DB_DATABASE'],
                          user=config['DB_USER'], password=config['DB_PASSWORD'])
        self.session: Session = conn.sess
        self.config = config
        self.link_src = read_link()
