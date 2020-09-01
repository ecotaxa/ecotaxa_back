# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os

# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from DB.Connection import Connection, check_sqlalchemy_version
from helpers.link_to_legacy import read_config, read_link


class BaseService(object):
    """
        A service, i.e. a stateless object which lives only for the time it does its job.
    """


#
# In postgresql.conf, postgresql has to listen to docker0 interface, typically:
#    listen_addresses = '127.0.0.1,172.17.0.1'       # what IP address(es) to listen on;
# as docker0 interface has 172.17.0.1 address
# Also in pg_hba.conf:
#    host    all             all             172.17.0.2/32           md5 or peer or trust
# as running docker processes are on 172.17.0.2
#
def _get_default_gateway():
    # TODO: somewhere else
    for a_line in open('/proc/net/route').readlines():
        # Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT
        # eth0	00000000	010011AC	0003	0	0	0	00000000	0	0	0
        fields = a_line.split()
        if fields[1] == "00000000":  # default route
            gw = fields[2]
            ip = [gw[i:i + 2] for i in range(6, -1, -2)]
            ip = [str(int(i, 16)) for i in ip]
            ip_str = ".".join(ip)
            return ip_str
    return ""


def _turn_localhost_for_docker(host: str, _port: str):
    """ Turn localhost to the address as seen from inside the container
        For win & mac0s there is a solution, environment var host.docker.internal
         but https://github.com/docker/for-linux/issues/264
    """
    if host == "localhost" and os.getcwd() == "/app":
        # noinspection PyBroadException
        try:
            return _get_default_gateway()
        except Exception:
            pass
    return host


class Service(BaseService):
    """
        A service for EcoTaxa. Supplies common useful features like a DB session and filesystem conventions.
    """
    the_config = None
    the_connection = None
    the_link = None

    def __init__(self):
        # Use a single configuration
        if not Service.the_config:
            config = read_config()
            Service.the_config = config
        else:
            config = Service.the_config
        # Use a single connection
        if not Service.the_connection:
            check_sqlalchemy_version()
            port = config['DB_PORT']
            if port is None:
                port = '5432'
            host = _turn_localhost_for_docker(config['DB_HOST'], port)
            conn = Connection(host=host, port=port, db=config['DB_DATABASE'],
                                                user=config['DB_USER'], password=config['DB_PASSWORD'])
            Service.the_connection = conn
        else:
            conn = Service.the_connection
        # And a single link
        if not Service.the_link:
            link_src = read_link()
            Service.the_link = link_src
        else:
            link_src = Service.the_link
        # Finally feed the subclass
        self.session: Session = conn.get_session()
        self.config = config
        self.link_src = link_src

    def __del__(self):
        # Release DB session
        self.session.close()


if __name__ == '__main__':
    _get_default_gateway()
