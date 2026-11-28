# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from unittest.mock import MagicMock, patch

import pytest

from API_operations.helpers.Service import Service
from BG_operations.ResourceCleaner import ResourceCleaner
from DB.helpers.Connection import Connection


@pytest.fixture
def clean_service_statics():
    saved_config = Service.the_config
    saved_conn = Service.the_connection
    saved_ro_conn = Service.the_readonly_connection
    Service.the_config = None
    Service.the_connection = None
    Service.the_readonly_connection = None
    try:
        yield
    finally:
        Service.the_config = saved_config
        Service.the_connection = saved_conn
        Service.the_readonly_connection = saved_ro_conn


def test_connection_dispose_delegates_to_engine():
    conn = Connection.__new__(Connection)
    conn.engine = MagicMock()

    conn.dispose()
    conn.engine.dispose.assert_called_once_with(close=True)

    conn.engine.dispose.reset_mock()
    conn.dispose(close=False)
    conn.engine.dispose.assert_called_once_with(close=False)


def test_service_close_connections_disposes_and_clears(clean_service_statics):
    mock_cfg = MagicMock()
    mock_conn = MagicMock()
    mock_ro_conn = MagicMock()
    Service.the_config = mock_cfg
    Service.the_connection = mock_conn
    Service.the_readonly_connection = mock_ro_conn

    Service.close_connections(close=False)

    mock_conn.dispose.assert_called_once_with(close=False)
    mock_ro_conn.dispose.assert_called_once_with(close=False)
    assert Service.the_connection is None
    assert Service.the_readonly_connection is None
    assert Service.the_config is mock_cfg

    # Calling again when already None is a safe no-op
    Service.close_connections()


def test_service_close_connections_clears_both_even_on_error(clean_service_statics):
    mock_conn = MagicMock()
    mock_conn.dispose.side_effect = RuntimeError("dispose failed")
    mock_ro_conn = MagicMock()
    Service.the_connection = mock_conn
    Service.the_readonly_connection = mock_ro_conn

    with pytest.raises(RuntimeError, match="dispose failed"):
        Service.close_connections()

    mock_ro_conn.dispose.assert_called_once_with(close=True)
    assert Service.the_connection is None
    assert Service.the_readonly_connection is None


def test_service_reset_clears_connections_and_config(clean_service_statics):
    mock_cfg = MagicMock()
    mock_conn = MagicMock()
    mock_ro_conn = MagicMock()
    Service.the_config = mock_cfg
    Service.the_connection = mock_conn
    Service.the_readonly_connection = mock_ro_conn

    Service.reset()

    mock_conn.dispose.assert_called_once_with(close=True)
    mock_ro_conn.dispose.assert_called_once_with(close=True)
    assert Service.the_connection is None
    assert Service.the_readonly_connection is None
    assert Service.the_config is None


def test_resource_cleaner_handles_cleared_connections(clean_service_statics):
    with patch("BG_operations.ResourceCleaner.regular_mem_cleanup") as mem_cleanup:
        ResourceCleaner.do_cleanup()
        mem_cleanup.assert_called_once_with()
