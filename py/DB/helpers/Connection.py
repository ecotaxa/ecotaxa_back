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
    expected_version = "1.4.31"
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

class Connection(object):
    """
        A connection to the DB via SQLAlchemy.
    """
    APP_NAME = "ecotaxa_back"

    def __init__(self, user, password, db, host, port=5432, read_only=False):
        """
            Open a SQLAlchemy connection, i.e. an engine.
        """
        if read_only:
            exec_options = {'postgresql_readonly': True}
        else:
            exec_options = {}
        # We connect with the help of the PostgreSQL URL
        url = 'postgresql://{}:{}@{}:{}/{}'
        url = url.format(user, password, host, port, db)
        engine = sqlalchemy.create_engine(url, client_encoding='utf8',
                                          echo=False, echo_pool=False,
                                          # echo=True, echo_pool="debug",
                                          executemany_mode='batch',
                                          # Reminder: QueuePool is default implementation
                                          # Avoid too many stale sessions, we need at max:
                                          # - 1 session for serving requests
                                          # - 1 session for knowing which jobs to run,
                                          #   _or running the job_ as we don't look for other jobs if one is running
                                          pool_size=2, max_overflow=1,
                                          # This way we can restart the DB and sessions will re-establish themselves
                                          # the cost is 1 (simple) query per connection pool recycle.
                                          pool_pre_ping=True,
                                          execution_options=exec_options,
                                          connect_args={"application_name": self.APP_NAME})
        self.session_factory = sessionmaker(bind=engine)
        self._meta: MetaData = sqlalchemy.MetaData(bind=engine)
        self._meta.reflect()
        self.engine = engine

    @property
    def url(self):
        return self.engine.url

    def get_session(self) -> Session:
        """
            Get a fresh or recycled session from the connection.
        """
        ret = self.session_factory()
        return ret

    def exec_outside_transaction(self, statement: str):
        """
            Execute raw SQL outside of any transaction (which is created by default by SQLA)
        """
        with self.engine.connect() as conn:
            conn.execute("commit")
            conn.execute(statement)

    def get_metadata(self) -> MetaData:
        """
            Get the metadata (for admin operations).
        """
        return self._meta
