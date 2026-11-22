# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

import pytest
import requests

from providers.EDMO import EDMOFetcher, EDMOOrganization


def _binding(code, name):
    return {
        "code": {
            "type": "literal",
            "datatype": "https://edmo.seadatanet.org/ontology#edmoCode",
            "value": code,
        },
        "name": {"type": "literal", "value": name},
    }


@pytest.fixture
def mock_session(mocker):
    session = MagicMock()
    mocker.patch.object(EDMOFetcher, "get_session", return_value=session)
    return session


def _response(status_code=200, bindings=None):
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = {"results": {"bindings": bindings or []}}
    return response


def test_find_by_name(mock_session):
    mock_session.get.return_value = _response(
        bindings=[_binding("1410", "Akvaplan-NIVA AS ")]
    )
    assert EDMOFetcher.find_by_name(" akvaplan-niva as") == [
        EDMOOrganization(1410, "Akvaplan-NIVA AS")
    ]
    args, kwargs = mock_session.get.call_args
    assert args == (EDMOFetcher.SPARQL_URL,)
    assert kwargs["timeout"] == EDMOFetcher.TIMEOUT
    # EDMO answers 404 to the default python-requests User-Agent
    assert kwargs["headers"] == {
        "Accept": "application/sparql-results+json",
        "User-Agent": EDMOFetcher.USER_AGENT,
    }
    sparql = kwargs["params"]["query"]
    assert 'lcase("akvaplan-niva as")' in sparql
    assert "org:name ?name" in sparql and "skos:notation ?code" in sparql


def test_find_by_name_escapes(mock_session):
    mock_session.get.return_value = _response()
    EDMOFetcher.find_by_name('Institute "Grigore" \\ Antipa')
    sparql = mock_session.get.call_args.kwargs["params"]["query"]
    assert r'lcase("Institute \"Grigore\" \\ Antipa")' in sparql


def test_find_by_name_empty(mock_session):
    assert EDMOFetcher.find_by_name("  ") == []
    mock_session.get.assert_not_called()


def test_get_by_code(mock_session):
    mock_session.get.return_value = _response(
        bindings=[_binding("1410", "Akvaplan-NIVA AS")]
    )
    assert EDMOFetcher.get_by_code(1410) == EDMOOrganization(1410, "Akvaplan-NIVA AS")
    sparql = mock_session.get.call_args.kwargs["params"]["query"]
    assert "<https://edmo.seadatanet.org/report/1410>" in sparql


def test_get_by_code_not_found(mock_session):
    mock_session.get.return_value = _response()
    assert EDMOFetcher.get_by_code(99999999) is None


def test_bad_bindings_ignored(mock_session):
    mock_session.get.return_value = _response(
        bindings=[{"name": {"value": "No code"}}, _binding("x", "Bad code")]
    )
    assert EDMOFetcher.find_by_name("anything") == []


def test_http_error(mocker, mock_session):
    mock_session.get.return_value = _response(status_code=500)
    spy_invalidate = mocker.spy(EDMOFetcher, "invalidate_session")
    assert EDMOFetcher.find_by_name("anything") == []
    assert spy_invalidate.called


def test_network_error(mocker, mock_session):
    mock_session.get.side_effect = requests.Timeout("too slow")
    spy_invalidate = mocker.spy(EDMOFetcher, "invalidate_session")
    assert EDMOFetcher.get_by_code(1410) is None
    assert spy_invalidate.called


def test_search(mock_session):
    mock_session.get.return_value = _response(
        bindings=[
            _binding("521", "Roscoff Marine Station, Sorbonne Université and CNRS"),
            _binding("4962", "Sorbonne University"),
        ]
    )
    assert EDMOFetcher.search(" Sorbonne ") == [
        EDMOOrganization(521, "Roscoff Marine Station, Sorbonne Université and CNRS"),
        EDMOOrganization(4962, "Sorbonne University"),
    ]
    sparql = mock_session.get.call_args.kwargs["params"]["query"]
    assert 'contains(lcase(str(?name)), lcase("Sorbonne"))' in sparql
    assert "LIMIT %d" % EDMOFetcher.MAX_SEARCH_RESULTS in sparql


def test_search_too_short(mock_session):
    assert EDMOFetcher.search(" ab ") == []
    mock_session.get.assert_not_called()
