import pytest
from fastapi import Response
from fastapi.testclient import TestClient

import main
from helpers.AppConfig import Config
from tests.fastapi_fixture import FAKE_SERVER


# Since the middleware is already added to main.app, we can just use the fastapi fixture
# or a fresh TestClient if we don't need the security patching.
# FixLocationMiddleware depends on Config().get_account_validation_url()


@pytest.fixture
def test_app():
    # Add a temporary route to test redirection
    @main.app.get("/test-redirect-internal")
    async def test_redirect_internal():
        # A redirect that should be caught by FixLocationMiddleware
        return Response(
            status_code=302, headers={"Location": "http://localhost:8000/some-path"}
        )

    @main.app.get("/test-redirect-external")
    async def test_redirect_external():
        # A redirect that should ALSO be caught because it matches http://[^/]+
        return Response(
            status_code=302, headers={"Location": "http://otherhost/some-path"}
        )

    @main.app.get("/test-redirect-relative")
    async def test_redirect_relative():
        return Response(status_code=302, headers={"Location": "/relative-path"})

    @main.app.get("/test-redirect-https")
    async def test_redirect_https():
        return Response(
            status_code=302, headers={"Location": "https://localhost:8000/some-path"}
        )

    @main.app.get("/test-redirect-no-slash")
    async def test_redirect_no_slash():
        # Test the match.group(1) or "/" logic
        return Response(status_code=302, headers={"Location": "http://localhost:8000"})

    yield main.app


def test_fix_location_middleware(config, test_app):
    client = TestClient(test_app)
    front_url = Config().get_account_validation_url()
    # Ensure front_url is what we expect from config.ini in tests
    assert front_url == FAKE_SERVER

    # Test internal-like redirect
    response = client.get("/test-redirect-internal", allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == f"{front_url}some-path"

    # Test external redirect
    response = client.get("/test-redirect-external", allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == f"{front_url}some-path"

    # Test relative redirect
    response = client.get("/test-redirect-relative", allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/relative-path"

    # Test https redirect are not damaged
    response = client.get("/test-redirect-https", allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://localhost:8000/some-path"

    # Test redirect with no path after host
    response = client.get("/test-redirect-no-slash", allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == front_url
