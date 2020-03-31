# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging

import sqlalchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker, Session


def check_sqlalchemy_version():
    version = sqlalchemy.__version__
    expected_version = "1.3.15"
    if version != expected_version:
        logging.error("Not the expected SQLAlchemy version (%s instead of %s), exiting to avoid data corruption",
                      version, expected_version)
        exit(-1)


class Connection(object):
    """
        A connection to the DB.
    """

    def __init__(self, user, password, db, host='localhost', port=5432):
        """
        Returns a connection and a metadata object
        """
        # We connect with the help of the PostgreSQL URL
        url = 'postgresql://{}:{}@{}:{}/{}'
        url = url.format(user, password, host, port, db)

        engine = sqlalchemy.create_engine(url, client_encoding='utf8', echo=False)
        session_factory = sessionmaker(bind=engine)
        self.sess: Session = session_factory()
        self.meta: MetaData = sqlalchemy.MetaData(bind=engine)
        self.meta.reflect()
