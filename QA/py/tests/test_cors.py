#
# CORS headers for known third-party browser apps, see ecotaxa/ecotaxa#29
# Allowed origins are set in env by fastapi_fixture, before main.py import.
#
import pytest

from tests.fastapi_fixture import CORS_ORIGIN

PLANKTOSCOPE_ORIGIN = "http://pkscope-sponge-bob.local"
UNKNOWN_ORIGIN = "https://evil.example"

ACAO = "access-control-allow-origin"


def preflight(fastapi, url, origin):
    return fastapi.options(
        url,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


@pytest.mark.parametrize("origin", [CORS_ORIGIN, PLANKTOSCOPE_ORIGIN])
def test_cors_preflight_allowed(fastapi, origin):
    rsp = preflight(fastapi, "/api/object/1", origin)
    assert rsp.status_code == 200
    assert rsp.headers.get_list(ACAO) == [origin]
    assert "authorization" in rsp.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in rsp.headers


@pytest.mark.parametrize(
    "origin",
    [
        UNKNOWN_ORIGIN,
        # Regex is anchored
        "http://pkscope-x.local.evil.example",
        "https://pkscope-x.local",
    ],
)
def test_cors_preflight_refused(fastapi, origin):
    rsp = preflight(fastapi, "/api/object/1", origin)
    assert rsp.status_code == 400
    assert ACAO not in rsp.headers


@pytest.mark.parametrize("url", ["/status", "/api/status", "/api/object/1"])
def test_cors_simple_request(fastapi, url):
    # /api/... goes through the middlewares twice due to app.mount("/api", app), header must not be doubled.
    # /api/object/1 is an error response (no auth), which also needs the header for the app to read the error.
    rsp = fastapi.get(url, headers={"Origin": PLANKTOSCOPE_ORIGIN})
    assert rsp.headers.get_list(ACAO) == [PLANKTOSCOPE_ORIGIN]
    assert "Origin" in rsp.headers["vary"]
    assert "access-control-allow-credentials" not in rsp.headers
    rsp = fastapi.get(url, headers={"Origin": UNKNOWN_ORIGIN})
    assert ACAO not in rsp.headers


def test_cors_no_origin(fastapi):
    # Same-origin (front) and non-browser clients send no Origin
    rsp = fastapi.get("/status")
    assert ACAO not in rsp.headers
