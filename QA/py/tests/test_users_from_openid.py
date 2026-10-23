import pytest
from API_operations.OpenID import normalize_user_info, oauth, THE_PROVIDER
from API_operations.CRUD.Users import UserService
from API_operations.helpers.UserValidation import ActivationType
from DB.User import User, UserOIDC, UserStatus
from helpers.AppConfig import Config
from helpers.httpexception import (
    DETAIL_OPENID_ACCOUNT_BLOCKED,
    DETAIL_OPENID_ACCOUNT_INACTIVE,
    DETAIL_OPENID_ACCOUNT_PENDING,
)
from tests.fastapi_fixture import FAKE_SERVER

# Matches tests/config.ini, and what the mocked providers return as "iss"
ISSUER = "https://my.keycloack.com/realms/theia"
TOKEN_HEADER = "X-Ecotaxa-Token"
ID_TOKEN_HEADER = "X-Ecotaxa-Id-Token"

# Representative payload for the provider's custom "earth-data" claim.
EARTH_DATA_USER_INFO = {
    "scope": "openid email profile",
    "email_verified": True,
    "name": "Otto Graph",
    "preferred_username": "otto.graph@example.org",
    "earth-data": {
        "country": "Germany",
        "organization": "GraphCorp",
        "organization-type": "research",
    },
    "given_name": "Otto",
    "family_name": "Graph",
    "email": "otto.graph@example.org",
}


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


def mock_user_info(sub: str, email: str, name: str = "A User", verified: bool = True):
    return {
        "iss": ISSUER,
        "sub": sub,
        "email": email,
        "email_verified": verified,
        "name": name,
    }


def assert_no_auth_cookies(response):
    assert "token" not in response.cookies
    assert "id_token" not in response.cookies


def test_normalize_earth_data_claims():
    """The provider nests organisation and country in the "earth-data" claim."""
    info = normalize_user_info(EARTH_DATA_USER_INFO)
    assert info == {
        "email": "otto.graph@example.org",
        "name": "Otto Graph",
        "organisation": "GraphCorp",
        "country": "Germany",
        "orcid": "",
        "usercreationreason": "Please fill in",
    }


def test_normalize_claim_fallbacks():
    """Missing nested claims fall back to the top-level ones or to "Unknown"."""
    info = normalize_user_info(
        {
            "email": "user@example.org",
            "name": "A User",
            "organization": "Top Level Org",
            "country": "",
        }
    )
    assert info["organisation"] == "Top Level Org"
    assert info["country"] == "Unknown"
    assert normalize_user_info({"email": "user@example.org"})["organisation"] == (
        "Unknown"
    )
    # Keycloak can send the organization membership as an object.
    info = normalize_user_info(
        {"organization": {"graphcorp": {"name": "GraphCorp"}}}
    )
    assert info["organisation"] == "GraphCorp"


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
            "issuer": ISSUER,
        },
    )

    # Initiate login
    response = fastapi.get("/openid/login", follow_redirects=False)
    # It should redirect to the provider's authorization endpoint
    assert response.status_code in [302, 307]
    location = response.headers.get("location")
    assert location is not None
    assert location.startswith("https://my.keycloack.com/realms/theia/")
    # The exact URL depends on the provider metadata, but it should contain some expected params
    assert "response_type=code" in location
    assert "client_id=" in location
    assert "scope=openid+email+profile" in location
    assert "prompt=login" not in location


@pytest.mark.asyncio
async def test_openid_login_force_login(config, fastapi, monkeypatch):
    """After an error, the next attempt must ignore the provider SSO session."""
    fastapi.cookies.clear()
    provider = get_provider()
    patch_metadata(
        monkeypatch,
        provider,
        {
            "authorization_endpoint": "https://my.keycloack.com/realms/theia/protocol/openid-connect/auth",
            "issuer": ISSUER,
        },
    )

    response = fastapi.get(
        "/openid/login?force_login=1", follow_redirects=False
    )
    assert response.status_code in [302, 307]
    location = response.headers.get("location")
    assert location is not None
    assert "prompt=login" in location


@pytest.mark.asyncio
async def test_login_linked_user(config, database, fastapi, monkeypatch):
    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # An existing account, explicitly linked to the provider identity
    email = "linked@users.com"
    with UserService() as sce:
        usr = User(
            email=email,
            name="Linked User",
            password="a-password",
            status=UserStatus.active.value,
        )
        sce.session.add(usr)
        sce.session.commit()
        user_id = usr.id
        sce.session.add(UserOIDC(user_id=user_id, issuer=ISSUER, subject="12345"))
        sce.session.commit()
    provider = get_provider()

    mock_token = {
        "userinfo": mock_user_info("12345", email),
        "access_token": "fake-token",
        "id_token": "more-fake-token",
    }

    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "abc", "state": "xyz"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    hdrs = response.headers
    assert hdrs.get("location") == FAKE_SERVER
    # Credentials are handed over in headers, not in browser cookies
    assert hdrs.get(TOKEN_HEADER)
    assert hdrs.get(ID_TOKEN_HEADER) == "more-fake-token"
    assert hdrs.get("cache-control") == "no-store"
    # It is a short-lived access token, not the legacy 31-day Flask token
    from helpers.fastApiUtils import ACCESS_SALT, build_serializer

    payload = build_serializer(ACCESS_SALT).loads(
        hdrs[TOKEN_HEADER], max_age=3600
    )
    assert payload["user_id"] == user_id
    assert_no_auth_cookies(response)
    # The token in the header is directly usable as a bearer
    with UserService() as sce:
        assert sce.find_by_oidc(ISSUER, "12345").id == user_id


@pytest.mark.asyncio
async def test_login_new_user(config, database, fastapi, monkeypatch):
    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # New user logs in with OpenID
    provider = get_provider()

    # Mock Authlib's internal token exchange
    email = "new_user@users.com"
    mock_token = {
        "userinfo": mock_user_info("67890", email, name="New User"),
        "access_token": "fake-token-2",
        "id_token": "more-fake-token-2",
    }

    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "def", "state": "uvw"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    hdrs = response.headers
    assert hdrs.get("location") == FAKE_SERVER
    assert hdrs.get(TOKEN_HEADER)
    assert hdrs.get(ID_TOKEN_HEADER) == "more-fake-token-2"
    assert_no_auth_cookies(response)

    # Verify user was created in DB, and linked to the identity
    with UserService() as sce:
        db_user = sce.find_by_email(email=email)
        assert db_user is not None
        assert db_user.name == "New User"
        assert db_user.usercreationreason == "Please fill in"
        # Registration policy: active because account validation is off in tests
        assert db_user.status == UserStatus.active.value
        assert sce.find_by_oidc(ISSUER, "67890").id == db_user.id


@pytest.mark.asyncio
async def test_login_earth_data_claims(config, database, fastapi, monkeypatch):
    """The client's exact payload is stored as organisation/country."""
    fastapi.cookies.clear()
    provider = get_provider()
    user_info = dict(EARTH_DATA_USER_INFO)
    user_info["iss"] = ISSUER
    user_info["sub"] = "earth-data-sub"
    mock_token = {
        "userinfo": user_info,
        "access_token": "fake-token-earth",
        "id_token": "more-fake-token-earth",
    }
    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "earth", "state": "data"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers.get(TOKEN_HEADER)

    with UserService() as sce:
        db_user = sce.find_by_oidc(ISSUER, "earth-data-sub")
        assert db_user is not None
        assert db_user.email == "otto.graph@example.org"
        assert db_user.name == "Otto Graph"
        assert db_user.organisation == "GraphCorp"
        assert db_user.country == "Germany"


@pytest.mark.asyncio
async def test_login_convert_guest(config, database, fastapi, monkeypatch):
    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()
    # Create a guest first
    from DB.User import Guest

    email = "guest@users.com"
    guest_name = "Original Guest"

    with UserService() as sce:
        # add_openid_user converts a Guest into a User when it finds one.
        guest = Guest(email=email, name=guest_name)
        sce.session.add(guest)
        sce.session.commit()

    # Guest logs in with OpenID
    provider = get_provider()

    mock_token = {
        "userinfo": mock_user_info("11223", email, name="Now A User"),
        "access_token": "fake-token-3",
        "id_token": "more-fake-token-3",
    }

    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "ghi", "state": "pqr"},
        follow_redirects=False,
    )
    assert response.status_code == 307

    # Verify guest was converted to user in DB
    with UserService() as sce:
        db_user = sce.find_by_email(email=email)
        assert db_user is not None
        # Check it is now a User, not a Guest (find_by_email returns User)
        from DB.User import Guest, User

        assert isinstance(db_user, User)
        # Check it's not a guest anymore
        q_guest = sce.session.query(Guest).filter(Guest.email == email).one_or_none()
        assert q_guest is None
        # The name should have been updated from OpenID info
        assert db_user.name == "Now A User"
        # ... and the identity is now persisted
        assert sce.find_by_oidc(ISSUER, "11223").id == db_user.id


@pytest.mark.asyncio
async def test_login_password_account_requires_explicit_linking(
    config, database, fastapi, monkeypatch
):
    """An email at the provider must not give access to a password-protected account."""
    fastapi.cookies.clear()
    email = "linked-conflict@users.com"
    with UserService() as sce:
        usr = User(
            email=email,
            name="Password Protected User",
            password="a-password",
            status=UserStatus.active.value,
        )
        sce.session.add(usr)
        sce.session.commit()
    provider = get_provider()
    mock_token = {
        "userinfo": mock_user_info("54321", email),
        "access_token": "fake-token-4",
        "id_token": "more-fake-token-4",
    }
    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "aaa", "state": "bbb"},
        follow_redirects=False,
    )
    assert response.status_code == 409
    assert_no_auth_cookies(response)
    with UserService() as sce:
        assert sce.find_by_oidc(ISSUER, "54321") is None


@pytest.mark.parametrize(
    "status,subject,email,expected",
    [
        (
            UserStatus.inactive.value,
            "password-inactive-sub",
            "password-inactive@users.com",
            DETAIL_OPENID_ACCOUNT_INACTIVE,
        ),
        (
            UserStatus.pending.value,
            "password-pending-sub",
            "password-pending@users.com",
            DETAIL_OPENID_ACCOUNT_PENDING,
        ),
        (
            UserStatus.blocked.value,
            "password-blocked-sub",
            "password-blocked@users.com",
            DETAIL_OPENID_ACCOUNT_BLOCKED,
        ),
    ],
)
@pytest.mark.asyncio
async def test_login_password_account_waiting_validation(
    config, database, fastapi, monkeypatch, status, subject, email, expected
):
    """The approval status wins over the password/OpenID link conflict."""
    fastapi.cookies.clear()
    with UserService() as sce:
        usr = User(
            email=email,
            name="Password Non Active User",
            password="a-password",
            status=status,
        )
        sce.session.add(usr)
        sce.session.commit()

    provider = get_provider()
    mock_token = {
        "userinfo": mock_user_info(subject, email, name="Password Non Active User"),
        "access_token": "fake-token-5b",
        "id_token": "more-fake-token-5b",
    }
    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "ccc2", "state": "ddd2"},
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == [expected]
    assert_no_auth_cookies(response)
    with UserService() as sce:
        assert sce.find_by_oidc(ISSUER, subject) is None


@pytest.mark.asyncio
async def test_new_openid_user_requests_admin_validation(
    config, database, fastapi, monkeypatch
):
    """With validation on, a new OpenID account enters the usual admin queue."""
    fastapi.cookies.clear()
    monkeypatch.setattr(Config, "get_account_validation", lambda self: "on")
    validation_requests = []

    def _capture_validation(
        self, user, ask_activate, inform_about_status, action_type
    ):
        validation_requests.append(
            (user.id, ask_activate, inform_about_status, action_type)
        )

    monkeypatch.setattr(UserService, "_conditional_validation", _capture_validation)

    email = "validation@users.com"
    provider = get_provider()
    mock_token = {
        "userinfo": mock_user_info("validation-sub", email, name="Validation User"),
        "access_token": "fake-token-5c",
        "id_token": "more-fake-token-5c",
    }
    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "ccc3", "state": "ddd3"},
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == [DETAIL_OPENID_ACCOUNT_INACTIVE]
    assert_no_auth_cookies(response)

    with UserService() as sce:
        db_user = sce.find_by_oidc(ISSUER, "validation-sub")
        assert db_user is not None
        assert db_user.status == UserStatus.inactive.value
        assert db_user.mail_status is True
        user_id = db_user.id
    assert validation_requests == [
        (user_id, True, False, ActivationType.create)
    ]


@pytest.mark.parametrize(
    "status,subject,email,expected",
    [
        (
            UserStatus.inactive.value,
            "inactive-sub",
            "inactive@users.com",
            DETAIL_OPENID_ACCOUNT_INACTIVE,
        ),
        (
            UserStatus.pending.value,
            "pending-sub",
            "pending@users.com",
            DETAIL_OPENID_ACCOUNT_PENDING,
        ),
        (
            UserStatus.blocked.value,
            "blocked-sub",
            "blocked@users.com",
            DETAIL_OPENID_ACCOUNT_BLOCKED,
        ),
    ],
)
@pytest.mark.asyncio
async def test_login_refused_for_non_active_user(
    config, database, fastapi, monkeypatch, status, subject, email, expected
):
    fastapi.cookies.clear()
    with UserService() as sce:
        usr = User(
            email=email,
            name="Non Active User",
            password=None,
            status=status,
        )
        sce.session.add(usr)
        sce.session.commit()
        sce.session.add(UserOIDC(user_id=usr.id, issuer=ISSUER, subject=subject))
        sce.session.commit()

    provider = get_provider()
    mock_token = {
        "userinfo": mock_user_info(subject, email, name="Non Active User"),
        "access_token": "fake-token-5",
        "id_token": "more-fake-token-5",
    }
    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "ccc", "state": "ddd"},
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == [expected]
    assert_no_auth_cookies(response)


@pytest.mark.asyncio
async def test_login_refused_for_unverified_email(
    config, database, fastapi, monkeypatch
):
    fastapi.cookies.clear()
    provider = get_provider()
    mock_token = {
        "userinfo": mock_user_info(
            "unverified-sub", "unverified@users.com", verified=False
        ),
        "access_token": "fake-token-6",
        "id_token": "more-fake-token-6",
    }
    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "eee", "state": "fff"},
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert_no_auth_cookies(response)
    with UserService() as sce:
        assert sce.find_by_email(email="unverified@users.com") is None


@pytest.mark.asyncio
async def test_email_lookup_does_not_interpret_wildcards(
    config, database, fastapi, monkeypatch
):
    """'_' in an email is a literal, it must not match another account."""
    fastapi.cookies.clear()
    with UserService() as sce:
        other = User(
            email="johnxdoe@users.com",
            name="John X Doe",
            password="some-password",
            status=UserStatus.active.value,
        )
        sce.session.add(other)
        sce.session.commit()

    provider = get_provider()
    mock_token = {
        "userinfo": mock_user_info("wildcard-sub", "john_doe@users.com"),
        "access_token": "fake-token-7",
        "id_token": "more-fake-token-7",
    }
    patch_authorize(monkeypatch, provider, mock_token)

    response = fastapi.get(
        "/openid/callback",
        params={"code": "ggg", "state": "hhh"},
        follow_redirects=False,
    )
    # A distinct account is created, the similar one is untouched
    assert response.status_code == 307
    with UserService() as sce:
        created = sce.find_by_email(email="john_doe@users.com")
        assert created is not None
        assert created.email != "johnxdoe@users.com"
        assert sce.find_by_oidc(ISSUER, "wildcard-sub").id == created.id


@pytest.mark.asyncio
async def test_openid_logout_redirects_to_provider(config, fastapi, monkeypatch):
    # Ensure provider exists and mock its metadata to include end_session_endpoint
    provider = get_provider()
    patch_metadata(
        monkeypatch,
        provider,
        {
            "end_session_endpoint": "https://my.keycloack.com/realms/theia/protocol/openid-connect/logout",
            "issuer": ISSUER,
        },
    )

    # Clear cookies to avoid interference from previous tests
    fastapi.cookies.clear()

    response = fastapi.get(
        "/openid/logout",
        headers={ID_TOKEN_HEADER: "logout-id-token"},
        follow_redirects=False,
    )
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
    assert qs.get("post_logout_redirect_uri", [None])[0] == FAKE_SERVER

    # The transient OIDC state cookie is dropped
    set_cookies = response.headers.get_list("set-cookie")
    assert any(
        c.startswith("oid_session=") and "max-age=0" in c.lower()
        for c in set_cookies
    )


@pytest.mark.asyncio
async def test_openid_logout_without_id_token(config, fastapi, monkeypatch):
    """No id_token_hint at all, rather than the string "None"."""
    provider = get_provider()
    patch_metadata(
        monkeypatch,
        provider,
        {
            "end_session_endpoint": "https://my.keycloack.com/realms/theia/protocol/openid-connect/logout",
            "issuer": ISSUER,
        },
    )
    fastapi.cookies.clear()

    response = fastapi.get("/openid/logout", follow_redirects=False)
    assert response.status_code in [302, 307]
    location = response.headers.get("location")
    assert location is not None

    from urllib.parse import urlparse, parse_qs

    qs = parse_qs(urlparse(location).query)
    assert "id_token_hint" not in qs
    assert "None" not in location
