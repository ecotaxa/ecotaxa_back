# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

import sqlalchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


def check_sqlalchemy_version():
    # noinspection PyUnresolvedReferences
    version = sqlalchemy.__version__
    expected_version = "1.4.14"
    if version != expected_version:  # pragma: no cover
        logger.fatal("Not the expected SQLAlchemy version (%s instead of %s), exiting to avoid data corruption",
                     version, expected_version)
        exit(-1)


# @listens_for(Pool, "connect")
# def my_on_connect(dbapi_conn, _conn_record):
#     # Fix for https://github.com/ecotaxa/ecotaxa_dev/issues/636
#     # Align the DB precision of floats with the one in python
#     # This is not necessary anymore with PG12+
#     # ref: https://www.postgresql.org/docs/12/datatype-numeric.html#DATATYPE-FLOAT
#     #  and https://www.postgresql.org/docs/11/runtime-config-client.html
#     # TODO: Remove when go to PG12+
#     crs = dbapi_conn.cursor()
#     crs.execute("set extra_float_digits=2")
#     crs.close()
#     dbapi_conn.commit()


class ReadOnlyQueuePool(QueuePool):
    def __init__(self, *args, **kwargs):
        kwargs['reset_on_return'] = None
        super().__init__(*args, **kwargs)


class Connection(object):
    """
        A connection to the DB via SQLAlchemy.
    """

    def __init__(self, user, password, db, host, port=5432, read_only=False):
        """
            Open a SQLAlchemy connection, i.e. an engine.
        """
        if read_only:
            pool_class = ReadOnlyQueuePool
        else:
            # Doc says: default for all dialects except SQLite
            pool_class = QueuePool
        # We connect with the help of the PostgreSQL URL
        url = 'postgresql://{}:{}@{}:{}/{}'
        url = url.format(user, password, host, port, db)
        engine = sqlalchemy.create_engine(url, client_encoding='utf8',
                                          echo=False, echo_pool=False,
                                          # echo=True, echo_pool="debug",
                                          executemany_mode='batch',
                                          poolclass=pool_class,
                                          # Not needed anyway it's not async anywhere and default is 5
                                          # pool_size=20, max_overflow=5,
                                          # This way we can restart the DB and sessions will re-establish themselves
                                          # the cost is 1 (simple) query per connection pool recycle.
                                          pool_pre_ping=True,
                                          connect_args={"application_name": "ecotaxa_back"})
        self.session_factory = sessionmaker(bind=engine)
        self._meta: MetaData = sqlalchemy.MetaData(bind=engine)
        self._meta.reflect()

    def get_session(self) -> Session:
        """
            Get a fresh or recycled session from the connection.
        """
        ret = self.session_factory()
        return ret
