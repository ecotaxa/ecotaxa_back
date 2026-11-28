# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging
import time
from typing import Any, ClassVar, Optional

import psycopg
import sqlalchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.util.queue import Queue

from helpers.AppConfig import Config
from helpers.CustomException import ServiceUnavailableException
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


def check_sqlalchemy_version() -> None:
    # noinspection PyUnresolvedReferences
    version = sqlalchemy.__version__
    expected_version = "2.0.51"
    if version != expected_version:  # pragma: no cover
        logger.fatal(
            "Not the expected SQLAlchemy version (%s instead of %s), exiting to avoid data corruption",
            version,
            expected_version,
        )
        exit(-1)


class TimeEvictedQueue(Queue):
    DB_SESSION_MAX_AGE: ClassVar[int] = (
        300  # No physical DB connection should live longer than 5m
    )
    CLEAN_INTERVAL: ClassVar[int] = 5  # Look for connections to expire every n sec

    def __init__(self, maxsize=0, use_lifo=False):
        assert (
            use_lifo
        ), "If not set, eviction fails"  # With FIFO we might end up reusing a fresh cnx while older ones are not closed
        super().__init__(maxsize, use_lifo=use_lifo)
        self.last_cleanup: float = 0

    def put(self, item, block=True, timeout=None):
        super().put(item, block, timeout)
        self.evict()

    def _put(self, item) -> None:
        if item.dbapi_connection is None:
            self.queue.appendleft(item)
            return
        now = time.time()
        if now - item.starttime > self.DB_SESSION_MAX_AGE:
            try:
                item.invalidate()
            except Exception as exc:
                logger.warning(
                    "Failed to invalidate expired DB connection on put: %s", exc
                )
            self.queue.appendleft(item)
            return
        self.queue.append(item)

    def evict(self) -> int:
        with self.mutex:
            now = time.time()
            if now - self.last_cleanup < self.CLEAN_INTERVAL:
                return 0
            ret = 0
            seen_live = False
            for a_conn in tuple(
                self.queue
            ):  # type: sqlalchemy.pool.base._ConnectionRecord
                is_expired = (
                    a_conn.dbapi_connection is not None
                    and now - a_conn.starttime > self.DB_SESSION_MAX_AGE
                )
                if is_expired:
                    # Note: invalidation is logged at INFO by the pool logger,
                    # which is set to WARNING below.
                    try:
                        a_conn.invalidate()
                        ret += 1
                    except Exception as exc:
                        logger.warning(
                            "Failed to invalidate expired DB connection: %s", exc
                        )
                if a_conn.dbapi_connection is None or is_expired:
                    if seen_live:
                        self.queue.remove(a_conn)
                        self.queue.appendleft(a_conn)
                else:
                    seen_live = True
            self.last_cleanup = now
            return ret


class TimeEvictedQueuePool(QueuePool):
    _queue_class = TimeEvictedQueue

    def __init__(
        self, creator, pool_size=5, max_overflow=10, timeout=30.0, use_lifo=False, **kw
    ):
        super().__init__(creator, pool_size, max_overflow, timeout, use_lifo, **kw)
        # A logger is created somewhere in inheritance chain, it gets the invalidation INFO messages, we don't want them
        logging.getLogger("DB.helpers.Connection.TimeEvictedQueuePool").setLevel(
            logging.WARNING
        )

    # Uncomment for debug
    # def _do_get(self):
    #     logger.info("Stats: %s", self.status())
    #     return QueuePool._do_get(self)


class DatabaseConnectionException(ServiceUnavailableException):
    """Raised when a database connection cannot be obtained from the pool"""


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
            exec_options = {
                "postgresql_readonly": True,
                # "isolation_level": "AUTOCOMMIT",
            }
        else:
            exec_options = {}
        # We connect with help of the PostgreSQL URL
        url = "postgresql+psycopg://{}:{}@{}:{}/{}"
        self.url = url.format(user, password, host, port, db)
        engine = sqlalchemy.create_engine(
            self.url,
            client_encoding="utf8",
            echo=False,
            echo_pool=False,
            # echo=True, echo_pool="debug",
            poolclass=TimeEvictedQueuePool,
            pool_use_lifo=True,
            # We have our own age-based eviction strategy; invalidated records stay in
            # the pool and reconnect on their next checkout.
            pool_size=6,
            max_overflow=4,
            # In case something goes unexpected, user will wait for this time for a free connection (or failure)
            pool_timeout=60,
            # This way we can restart the DB and sessions will re-establish themselves.
            # It also catches connections that died while idle between sweeps.
            # The cost is 1 (simple) query per connection checkout.
            pool_pre_ping=True,
            execution_options=exec_options,
            connect_args={
                "application_name": self.APP_NAME,
                # Big data options
                "options": "-c enable_partitionwise_join=on -c enable_partitionwise_aggregate=on",
            },
            future=True,
            query_cache_size=64,
            # Default cache_size is up to 500*1.5, but we have big text in queries, e.g. all obj_field columns
        )
        self.session_factory = sessionmaker(bind=engine)
        self._meta: Optional[MetaData] = None
        self.engine = engine

    def get_session(self) -> Session:
        """
        Get a fresh or recycled session from the connection.
        """
        ret = self.session_factory()
        # SQLAlchemy 2.0 is lazy, only feeds a real PG session when used.
        # But it delays problems if we run out of resources.
        try:
            ret.connection()
        except Exception as exc:
            try:
                ret.close()
            except Exception:
                pass
            raise DatabaseConnectionException("Failed to get a DB connection") from exc
        return ret

    def cleanup_pool(self) -> int:
        return self.engine.pool._pool.evict()  # type: ignore

    def dispose(self, close: bool = True) -> None:
        """
        Dispose the SQLAlchemy engine and its connection pool.
        Set close=False after fork to detach inherited sockets without closing them.
        """
        self.engine.dispose(close=close)

    def exec_outside_transaction(self, statement: str) -> None:
        """
        Execute raw SQL outside any transaction (which is created by default by SQLA)
        """
        with self.engine.connect() as conn:
            assert conn.connection.dbapi_connection
            conn.connection.dbapi_connection.autocommit = True
            conn.exec_driver_sql(statement)

    def get_metadata(self) -> MetaData:
        """
        Get the metadata (for admin operations). Reflected on first use only, as
        reflecting the whole schema is slow and not needed for regular serving.
        """
        if self._meta is None:
            self._meta = sqlalchemy.MetaData()
            self._meta.reflect(bind=self.engine)
        return self._meta

    @staticmethod
    def get_raw_psycopg_connection(read_only: bool = False) -> psycopg.Connection[Any]:
        """
        Open a standalone raw psycopg Connection independent of SQLAlchemy,
        using the application Config singleton.
        Caller is responsible for closing it (e.g. using a `with` statement).
        """
        config = Config()
        host, port, db = config.get_db_address(read_only)
        user, password = config.get_db_credentials(read_only)
        conn = psycopg.connect(
            user=user,
            password=password,
            dbname=db,
            host=host,
            port=port,
            application_name=Connection.APP_NAME,
            options="-c enable_partitionwise_join=on -c enable_partitionwise_aggregate=on",
            client_encoding="utf8",
        )
        if read_only:
            conn.read_only = True
        return conn
