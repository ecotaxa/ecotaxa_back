# -*- coding: utf-8 -*-
import threading
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
    response.__enter__.return_value = response
    response.__exit__.return_value = False
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


def test_response_closed_on_early_return_and_json_error(mocker, mock_session):
    rsp_204 = _response(status_code=204)
    mock_session.get.return_value = rsp_204
    assert EDMOFetcher.find_by_name("anything") == []
    rsp_204.__enter__.assert_called_once()
    rsp_204.__exit__.assert_called_once()

    rsp_500 = _response(status_code=500)
    mock_session.get.return_value = rsp_500
    assert EDMOFetcher.find_by_name("anything") == []
    rsp_500.__enter__.assert_called_once()
    rsp_500.__exit__.assert_called_once()

    rsp_bad_json = _response(status_code=200)
    rsp_bad_json.json.side_effect = ValueError("invalid json")
    mock_session.get.return_value = rsp_bad_json
    spy_invalidate = mocker.spy(EDMOFetcher, "invalidate_session")
    assert EDMOFetcher.find_by_name("anything") == []
    rsp_bad_json.__enter__.assert_called_once()
    rsp_bad_json.__exit__.assert_called_once()
    assert spy_invalidate.called


def test_invalidate_session_closes_session(mocker):
    EDMOFetcher.invalidate_session()
    created_sessions = []
    session_cls = requests.Session

    def make_session():
        sess = MagicMock(spec=session_cls)
        created_sessions.append(sess)
        return sess

    mocker.patch("providers.EDMO.requests.Session", side_effect=make_session)

    session = EDMOFetcher.get_session()
    assert session is created_sessions[0]
    assert EDMOFetcher.the_session is session

    EDMOFetcher.invalidate_session()
    assert EDMOFetcher.the_session is None
    session.close.assert_called_once()

    # Subsequent invalidation is a no-op
    EDMOFetcher.invalidate_session()
    session.close.assert_called_once()


def test_get_session_and_invalidate_thread_safe(mocker):
    EDMOFetcher.invalidate_session()
    created_sessions = []
    barrier = threading.Barrier(8)
    session_cls = requests.Session

    def make_session():
        sess = MagicMock(spec=session_cls)
        created_sessions.append(sess)
        return sess

    mocker.patch("providers.EDMO.requests.Session", side_effect=make_session)

    results = []

    def worker():
        barrier.wait()
        results.append(EDMOFetcher.get_session())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(created_sessions) == 1
    assert all(s is created_sessions[0] for s in results)

    # Concurrent invalidations should close the session exactly once
    inv_barrier = threading.Barrier(8)

    def inv_worker():
        inv_barrier.wait()
        EDMOFetcher.invalidate_session()

    inv_threads = [threading.Thread(target=inv_worker) for _ in range(8)]
    for t in inv_threads:
        t.start()
    for t in inv_threads:
        t.join()

    assert EDMOFetcher.the_session is None
    created_sessions[0].close.assert_called_once()
