# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from DB.helpers.Connection import Connection, DatabaseConnectionException
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
