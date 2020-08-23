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
    version = sqlalchemy.__version__
    expected_version = "1.3.17"
    if version != expected_version:  # pragma: no cover
        logger.fatal("Not the expected SQLAlchemy version (%s instead of %s), exiting to avoid data corruption",
                     version, expected_version)
        exit(-1)


class Connection(object):
    """
        A connection to the DB via SQLAlchemy.
    """
    the_session_factory = None

    def __init__(self, user, password, db, host, port=5432):
        """
        Returns a connection and a metadata object
        """
        # We connect with the help of the PostgreSQL URL
        url = 'postgresql://{}:{}@{}:{}/{}'
        url = url.format(user, password, host, port, db)

        if Connection.the_session_factory is None:
            # TODO: Not nice, no recovery in case of connection issue.
            engine = sqlalchemy.create_engine(url, client_encoding='utf8', echo=False)
            Connection.the_session_factory = sessionmaker(bind=engine)
            self._meta: MetaData = sqlalchemy.MetaData(bind=engine)
            self._meta.reflect()

        self.sess: Session = Connection.the_session_factory()
