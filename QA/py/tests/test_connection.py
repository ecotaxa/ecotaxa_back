# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from DB.helpers.Connection import (
    Connection,
    DatabaseConnectionException,
    TimeEvictedQueue,
)
from helpers.CustomException import BaseAppException, ServiceUnavailableException


def test_get_session_success():
    conn = Connection.__new__(Connection)
    mock_session = MagicMock()
    conn.session_factory = MagicMock(return_value=mock_session)

    session = conn.get_session()

    assert session is mock_session
    mock_session.connection.assert_called_once_with()
    mock_session.close.assert_not_called()


def test_get_session_raises_database_connection_exception():
    conn = Connection.__new__(Connection)
    mock_session = MagicMock()
    cause = SQLAlchemyTimeoutError("QueuePool limit reached")
    mock_session.connection.side_effect = cause
    conn.session_factory = MagicMock(return_value=mock_session)

    with pytest.raises(DatabaseConnectionException) as exc_info:
        conn.get_session()

    exc = exc_info.value
    assert not isinstance(exc, RuntimeError)
    assert isinstance(exc, ServiceUnavailableException)
    assert isinstance(exc, BaseAppException)
    assert exc.status_code == 503
    assert exc.__cause__ is cause
    mock_session.close.assert_called_once_with()


def _make_conn_record(
    starttime: float, dbapi_conn: object = object(), fail_invalidate: bool = False
):
    rec = MagicMock()
    rec.starttime = starttime
    rec.dbapi_connection = dbapi_conn

    def invalidate():
        if fail_invalidate:
            raise RuntimeError("close failed")
        rec.dbapi_connection = None

    rec.invalidate.side_effect = invalidate
    return rec


def test_evict_continues_after_invalidate_failure_and_updates_last_cleanup():
    q = TimeEvictedQueue(maxsize=6, use_lifo=True)
    now = 1000.0
    c_fail = _make_conn_record(starttime=now - 400, fail_invalidate=True)
    c_exp1 = _make_conn_record(starttime=now - 350)
    c_live = _make_conn_record(starttime=now - 50)
    c_exp2 = _make_conn_record(starttime=now - 310)
    q.queue.extend([c_fail, c_exp1, c_live, c_exp2])

    with patch("DB.helpers.Connection.time.time", return_value=now):
        evicted = q.evict()

    assert evicted == 2
    assert q.last_cleanup == now
    c_fail.invalidate.assert_called_once_with()
    c_exp1.invalidate.assert_called_once_with()
    c_exp2.invalidate.assert_called_once_with()
    c_live.invalidate.assert_not_called()
    # Live connection must be at the LIFO pop end, ahead of empty/failed slots
    assert q.get_nowait() is c_live


def test_evict_moves_invalidated_slots_away_from_lifo_pop_end():
    q = TimeEvictedQueue(maxsize=6, use_lifo=True)
    now = 1000.0
    c_live_older = _make_conn_record(starttime=now - 100)
    c_live_newer = _make_conn_record(starttime=now - 20)
    c_exp1 = _make_conn_record(starttime=now - 310)
    c_exp2 = _make_conn_record(starttime=now - 320)
    q.queue.extend([c_live_older, c_live_newer, c_exp1, c_exp2])

    with patch("DB.helpers.Connection.time.time", return_value=now):
        evicted = q.evict()

    assert evicted == 2
    assert c_exp1.dbapi_connection is None
    assert c_exp2.dbapi_connection is None
    assert q.get_nowait() is c_live_newer
    assert q.get_nowait() is c_live_older
    assert q.get_nowait() in (c_exp1, c_exp2)
    assert q.get_nowait() in (c_exp1, c_exp2)


def test_put_evicts_expired_connection_even_within_clean_interval():
    q = TimeEvictedQueue(maxsize=6, use_lifo=True)
    now = 1000.0
    q.last_cleanup = now - 1.0  # Within CLEAN_INTERVAL (5s)

    c_live = _make_conn_record(starttime=now - 30)
    c_expired = _make_conn_record(starttime=now - 350)

    with patch("DB.helpers.Connection.time.time", return_value=now):
        q.put_nowait(c_live)
        q.put_nowait(c_expired)

    c_expired.invalidate.assert_called_once_with()
    assert c_expired.dbapi_connection is None
    # Live connection remains at the LIFO pop end
    assert q.get_nowait() is c_live
    assert q.get_nowait() is c_expired


def test_put_moves_already_invalidated_and_failed_expired_to_bottom():
    q = TimeEvictedQueue(maxsize=6, use_lifo=True)
    now = 1000.0
    q.last_cleanup = now - 1.0

    c_live = _make_conn_record(starttime=now - 10)
    c_empty = _make_conn_record(starttime=now - 10, dbapi_conn=None)
    c_exp_fail = _make_conn_record(starttime=now - 400, fail_invalidate=True)

    with patch("DB.helpers.Connection.time.time", return_value=now):
        q.put_nowait(c_live)
        q.put_nowait(c_empty)
        q.put_nowait(c_exp_fail)

    c_exp_fail.invalidate.assert_called_once_with()
    assert q.get_nowait() is c_live
