# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

import sqlalchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker, Session

from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


def check_sqlalchemy_version():
    # noinspection PyUnresolvedReferences
    version = sqlalchemy.__version__
    expected_version = "1.3.22"
    if version != expected_version:  # pragma: no cover
        logger.fatal("Not the expected SQLAlchemy version (%s instead of %s), exiting to avoid data corruption",
                     version, expected_version)
        exit(-1)


class Connection(object):
    """
        A connection to the DB via SQLAlchemy.
    """

    def __init__(self, user, password, db, host, port=5432):
        """
            Open a SQLAlchemy connection, i.e. an engine.
        """
        # We connect with the help of the PostgreSQL URL
        url = 'postgresql://{}:{}@{}:{}/{}'
        url = url.format(user, password, host, port, db)
        engine = sqlalchemy.create_engine(url, client_encoding='utf8',
                                          echo=False, echo_pool=True,
                                          executemany_mode='batch',
                                          # Not needed anyway it's not async anywhere
                                          # pool_size=20, max_overflow=5,
                                          # This way we can restart the DB and re-establish sessions
                                          pool_pre_ping=True,
                                          connect_args={"application_name": "ecotaxa_back"})
        self.session_factory = sessionmaker(bind=engine)
        self._meta: MetaData = sqlalchemy.MetaData(bind=engine)
        self._meta.reflect()

    def get_session(self) -> Session:
        """
            Get a fresh session from the connection.
        """
        ret = self.session_factory()
        # Align the DB precision of floats with the one in python
        # This is not necessary anymore with PG12+
        # ref: https://www.postgresql.org/docs/12/datatype-numeric.html#DATATYPE-FLOAT
        #  and https://www.postgresql.org/docs/11/runtime-config-client.html
        # TODO: Remove when go to PG12
        ret.execute("set extra_float_digits=2")
        return ret
