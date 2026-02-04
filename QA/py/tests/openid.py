import pytest
from API_operations.OpenID import oauth, THE_PROVIDER


def get_provider():
    provider = getattr(oauth, THE_PROVIDER, None)
    assert provider is not None
    return provider


def patch_authorize(monkeypatch, provider, token):
    async def _mock_authorize(request):
        return token

    monkeypatch.setattr(provider, "authorize_access_token", _mock_authorize)


def patch_metadata(monkeypatch, provider, data: dict):
    async def _mock_load_server_metadata():
        return data

    monkeypatch.setattr(provider, "load_server_metadata", _mock_load_server_metadata)


@pytest.mark.asyncio
async def test_openid_login(config, fastapi, monkeypatch):
    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # Prevent network calls to the real/fake provider by mocking metadata fetching
    provider = get_provider()
    patch_metadata(
        monkeypatch,
        provider,
        {
            "authorization_endpoint": "https://my.keycloack.com/realms/theia/protocol/openid-connect/auth",
            "issuer": "https://my.keycloack.com/realms/theia",
        },
    )

    # Initiate login
    response = fastapi.get("/openid/login", allow_redirects=False)
    # It should redirect to the provider's authorization endpoint
    assert response.status_code in [302, 307]
    location = response.headers.get("location")
    assert location is not None
    assert location.startswith("https://my.keycloack.com/realms/theia/")
    # The exact URL depends on the provider metadata, but it should contain some expected params
    assert "response_type=code" in location
    assert "client_id=" in location
    assert "scope=openid+email+profile" in location


@pytest.mark.asyncio
async def test_login_existing_user(config, database, fastapi, monkeypatch):
    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # Admin user logs in with OpenID
    provider = get_provider()

    # Mock Authlib's internal token exchange
    mock_token = {
        "userinfo": {"email": "real@users.com", "sub": "12345"},
        "access_token": "fake-token",
        "id_token": "more-fake-token",
    }

    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "abc", "state": "xyz"},
        allow_redirects=False,
    )
    assert response.status_code == 307
    hdrs = response.headers
    assert hdrs.get("location") == "http://localhost:8000/"  # From ini
    cooks = response.cookies
    assert {"token", "id_token"}.issubset(set(cooks.iterkeys()))


@pytest.mark.asyncio
async def test_login_new_user(config, database, fastapi, monkeypatch):
    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # New user logs in with OpenID
    provider = get_provider()

    # Mock Authlib's internal token exchange
    email = "new_user@users.com"
    mock_token = {
        "userinfo": {"email": email, "sub": "67890", "name": "New User"},
        "access_token": "fake-token-2",
        "id_token": "more-fake-token-2",
    }

    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "def", "state": "uvw"},
        allow_redirects=False,
    )
    assert response.status_code == 307
    hdrs = response.headers
    assert hdrs.get("location") == "http://localhost:8000/"
    cooks = response.cookies
    assert {"token", "id_token"}.issubset(set(cooks.iterkeys()))

    # Verify user was created in DB
    from API_operations.CRUD.Users import UserService

    with UserService() as sce:
        db_user = sce.find_by_email(email=email)
        assert db_user is not None
        assert db_user.name == "New User"
        assert db_user.usercreationreason == "OpenID auto-registration"


@pytest.mark.asyncio
async def test_login_convert_guest(config, database, fastapi, monkeypatch):
    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # Create a guest first
    from API_operations.CRUD.Users import UserService

    email = "guest@users.com"
    guest_name = "Original Guest"

    with UserService() as sce:
        # We need to manually insert a guest or use a method that creates one.
        # add_openid_user handles Guest if it finds one.
        from DB.User import Guest

        guest = Guest(email=email, name=guest_name)
        sce.session.add(guest)
        sce.session.commit()

    # Guest logs in with OpenID
    provider = get_provider()

    # Mock Authlib's internal token exchange
    mock_token = {
        "userinfo": {"email": email, "sub": "11223", "name": "Now A User"},
        "access_token": "fake-token-3",
        "id_token": "more-fake-token-3",
    }

    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "ghi", "state": "pqr"},
        allow_redirects=False,
    )
    assert response.status_code == 307

    # Verify guest was converted to user in DB
    with UserService() as sce:
        db_user = sce.find_by_email(email=email)
        assert db_user is not None
        # Check it is now a User, not a Guest (find_by_email returns User)
        from DB.User import User, Guest

        assert isinstance(db_user, User)
        # Check it's not a guest anymore
        q_guest = sce.session.query(Guest).filter(Guest.email == email).one_or_none()
        assert q_guest is None
        # The name should have been updated from OpenID info
        assert db_user.name == "Now A User"


@pytest.mark.asyncio
async def test_openid_logout_redirects_to_provider(config, fastapi, monkeypatch):
    # Ensure provider exists and mock its metadata to include end_session_endpoint
    provider = get_provider()
    patch_metadata(
        monkeypatch,
        provider,
        {
            "end_session_endpoint": "https://my.keycloack.com/realms/theia/protocol/openid-connect/logout",
            "issuer": "https://my.keycloack.com/realms/theia",
        },
    )

    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # Provide an id_token cookie so it is propagated as id_token_hint
    fastapi.cookies.set("id_token", "logout-id-token")

    response = fastapi.get("/openid/logout", allow_redirects=False)
    assert response.status_code in [302, 307]
    location = response.headers.get("location")
    assert location is not None

    # Validate redirect target and query parameters
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(location)
    assert parsed.scheme == "https"
    assert parsed.netloc == "my.keycloack.com"
    assert parsed.path.endswith("/protocol/openid-connect/logout")

    qs = parse_qs(parsed.query)
    assert qs.get("id_token_hint", [None])[0] == "logout-id-token"
    # From tests config.ini
    assert qs.get("client_id", [None])[0] == "ecotaxa"
    assert qs.get("post_logout_redirect_uri", [None])[0] == "http://localhost:8000/"
