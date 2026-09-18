from typing import Any, Dict, List, Optional, Union
import pytest


class MockEcoTaxoServer:
    """
    Mock helper for EcoTaxoServerClient calls.
    Provides default responses for standard endpoints and allows customizing
    responses per endpoint or with specific return values.
    """

    def __init__(self, mocker: Any) -> None:
        self.mocker = mocker
        self.mock_call = mocker.patch(
            "providers.EcoTaxoServer.EcoTaxoServerClient.call"
        )
        self.taxa_updates: Union[List[Dict[str, Any]], Dict[str, Any]] = []
        self.setstat_response: Dict[str, Any] = {"msg": "ok"}
        self.settaxon_response: Dict[str, Any] = {"msg": "ok", "id": 789999}
        self.custom_responses: Dict[str, Any] = {}
        self.mock_call.side_effect = self._dispatch

    def _dispatch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "post",
    ) -> Any:
        resp = self.mocker.Mock()
        if endpoint in self.custom_responses:
            val = self.custom_responses[endpoint]
            if callable(val):
                resp.json.return_value = val(endpoint, params, method)
            else:
                resp.json.return_value = val
        elif endpoint == "/gettaxon/":
            resp.json.return_value = self.taxa_updates
        elif endpoint == "/setstat/":
            resp.json.return_value = self.setstat_response
        elif endpoint == "/settaxon/":
            resp.json.return_value = self.settaxon_response
        else:
            resp.json.return_value = {}
        return resp


@pytest.fixture
def mock_taxoserver(mocker: Any) -> MockEcoTaxoServer:
    return MockEcoTaxoServer(mocker)
