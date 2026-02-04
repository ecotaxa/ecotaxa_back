import pytest
from API_operations.OpenID import oauth, THE_PROVIDER


@pytest.mark.asyncio
async def test_login_ok(config, database, fastapi, monkeypatch):
    # Admin user logs in with OpenID
    provider = getattr(oauth, THE_PROVIDER, None)
    assert provider is not None

    # Mock Authlib's internal token exchange
    mock_token = {
        "userinfo": {"email": "real@users.com", "sub": "12345"},
        "access_token": "fake-token",
        "id_token": "more-fake-token"
    }

    async def mock_authorize(request):
        return mock_token

    monkeypatch.setattr(
        provider,
        "authorize_access_token",
        mock_authorize,
    )

    response = fastapi.get("/openid/callback", params={"code": "abc", "state": "xyz"}, allow_redirects=False)
    assert response.status_code == 307
    hdrs = response.headers
    assert hdrs.get("location") == "http://localhost:8000/"  # From ini
    cooks = response.cookies
    assert set(cooks.iterkeys()) == {"token", "id_token"}
