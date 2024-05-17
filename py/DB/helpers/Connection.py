# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
import time
from typing import ClassVar

import sqlalchemy
from sqlalchemy import MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.util.queue import Queue

from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


def check_sqlalchemy_version() -> None:
    # noinspection PyUnresolvedReferences
    version = sqlalchemy.__version__
    expected_version = "1.4.31"
    if version != expected_version:  # pragma: no cover
        logger.fatal(
            "Not the expected SQLAlchemy version (%s instead of %s), exiting to avoid data corruption",
            version,
            expected_version,
        )
        exit(-1)


class TimeEvictedQueue(Queue):
    DB_SESSION_MAX_AGE: ClassVar[
        int
    ] = 300  # No inactive session should be older than 5m
    CLEAN_INTERVAL: ClassVar[int] = 5  # Find sessions to expire after every n sec

    def __init__(self, maxsize=0, use_lifo=False):
        assert (
            use_lifo
        ), "If not set, eviction fails"  # With FIFO we might end up reusing a fresh cnx while older ones are not closed
        super().__init__(maxsize, use_lifo=use_lifo)
        self.last_cleanup: float = 0

    def put(self, item, block=True, timeout=None):
        super().put(item, block, timeout)
        now = time.time()
        if now - self.last_cleanup < self.CLEAN_INTERVAL:
            return
        self.last_cleanup = now
        with self.mutex:
            for a_conn in self.queue:  # type:sqlalchemy.pool.base._ConnectionRecord
                if (
                    a_conn.dbapi_connection
                    and now - a_conn.starttime > self.DB_SESSION_MAX_AGE
                ):
                    # Note: below produces info logs for each invalidation in global logger, if set.
                    a_conn.invalidate()


class TimeEvictedQueuePool(QueuePool):
    _queue_class = TimeEvictedQueue

    def __init__(
        self, creator, pool_size=5, max_overflow=10, timeout=30.0, use_lifo=False, **kw
    ):
        super().__init__(creator, pool_size, max_overflow, timeout, use_lifo, **kw)
        # A logger is created somewhere in inheritance chain, it gets the invalidation INFO messages, we don't want them
        q_logger = logging.getLogger()
        q_logger.disabled = True
        setattr(self, "logger", q_logger)

    # Uncomment for debug
    # def _do_get(self):
    #     logger.info("Stats: %s", self.status())
    #     return QueuePool._do_get(self)


class Connection(object):
    """
    A connection to the DB via SQLAlchemy.
    """

    APP_NAME: ClassVar = "ecotaxa_back"

    def __init__(
        self,
        user: str,
        password: str,
        db: str,
        host: str,
        port: int = 5432,
        read_only: bool = False,
    ):
        """
        Open a SQLAlchemy connection, i.e. an engine.
        """
        if read_only:
            exec_options = {"postgresql_readonly": True}
        else:
            exec_options = {}
        # We connect with the help of the PostgreSQL URL
        url = "postgresql://{}:{}@{}:{}/{}"
        url = url.format(user, password, host, port, db)
        engine = sqlalchemy.create_engine(
            url,
            client_encoding="utf8",
            echo=False,
            echo_pool=False,
            # echo=True, echo_pool="debug",
            executemany_mode="batch",
            poolclass=TimeEvictedQueuePool,
            pool_use_lifo=True,
            # We have our own age-based eviction strategy, the pool below will contain invalidated connections
            pool_size=16,
            max_overflow=8,
            # In case something goes unexpected, user will wait for this time for a free connection (or failure)
            pool_timeout=60,
            # This way we can restart the DB and sessions will re-establish themselves
            # The cost is 1 (simple) query per connection pool recycle.
            # Important: The invalidation mechanism now depends on it.
            pool_pre_ping=True,
            execution_options=exec_options,
            connect_args={"application_name": self.APP_NAME},
            future=True,
        )
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

    def exec_outside_transaction(self, statement: str) -> None:
        """
        Execute raw SQL outside any transaction (which is created by default by SQLA)
        """
        with self.engine.connect() as conn:
            conn.execute(text("commit"))
            conn.execute(text(statement))

    def get_metadata(self) -> MetaData:
        """
        Get the metadata (for admin operations).
        """
        return self._meta
