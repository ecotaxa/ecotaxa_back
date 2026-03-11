# -*- coding: utf-8 -*-
import pytest
import requests
from unittest.mock import MagicMock
from providers.NERC import NERCFetcher


@pytest.fixture
def mock_response():
    def _mock_response(status_code=200, json_data=None):
        response = MagicMock()
        response.status_code = status_code
        response.ok = 200 <= status_code < 300
        if json_data:
            response.json.return_value = json_data
        return response

    return _mock_response


def test_get_preferred_name_success(mocker, mock_response):
    # Mocking requests.Session.get
    mock_session = MagicMock()
    mocker.patch.object(NERCFetcher, "get_session", return_value=mock_session)

    vocab_url = "http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/"
    expected_name = "Hydroptic Underwater Vision Profiler 6 LP {UVP6} imaging sensor"

    json_data = {"skos:prefLabel": {"@value": expected_name}}

    mock_session.get.return_value = mock_response(json_data=json_data)

    result = NERCFetcher.get_preferred_name(vocab_url)

    assert result == expected_name
    mock_session.get.assert_called_once_with(
        vocab_url + NERCFetcher.JSON_REQ, timeout=5
    )


def test_get_preferred_name_not_ok(mocker, mock_response):
    mock_session = MagicMock()
    mocker.patch.object(NERCFetcher, "get_session", return_value=mock_session)
    # Ensure session is reset
    NERCFetcher.invalidate_session()

    vocab_url = "http://vocab.nerc.ac.uk/collection/L22/current/INVALID/"
    mock_session.get.return_value = mock_response(status_code=404)

    # We also want to check if invalidate_session was called.
    spy_invalidate = mocker.spy(NERCFetcher, "invalidate_session")

    result = NERCFetcher.get_preferred_name(vocab_url)

    assert result == ""
    assert spy_invalidate.called


def test_get_preferred_name_no_content(mocker, mock_response):
    mock_session = MagicMock()
    mocker.patch.object(NERCFetcher, "get_session", return_value=mock_session)

    vocab_url = "http://vocab.nerc.ac.uk/collection/L22/current/TOOL1578/"
    mock_session.get.return_value = mock_response(status_code=204)

    result = NERCFetcher.get_preferred_name(vocab_url)

    assert result == ""


def test_get_preferred_name_wrong_base_url():
    with pytest.raises(AssertionError):
        NERCFetcher.get_preferred_name("http://example.com/vocab")


def test_session_management():
    # Reset session
    NERCFetcher.invalidate_session()
    assert NERCFetcher.the_session is None

    session1 = NERCFetcher.get_session()
    assert isinstance(session1, requests.Session)
    assert NERCFetcher.the_session is session1

    session2 = NERCFetcher.get_session()
    assert session1 is session2

    NERCFetcher.invalidate_session()
    assert NERCFetcher.the_session is None

    session3 = NERCFetcher.get_session()
    assert session3 is not session1
