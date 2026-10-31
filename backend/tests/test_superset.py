from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from httpx import AsyncClient

from app.core.config import settings
from app.schemas.superset import SupersetGuestTokenResponse
from app.services.superset_service import SupersetService
from app.core.exceptions import SupersetIntegrationError


@pytest.mark.asyncio
async def test_guest_token_denied_for_unpermitted_dashboard(client: AsyncClient, seed_data):
    """User cannot generate a guest token for a dashboard they lack permissions for."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@bank.internal", "password": "ManagerPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = login_res.cookies[settings.CSRF_COOKIE_NAME]

    exec_dashboard_id = seed_data["dash_exec"].id

    res = await client.post(
        "/api/v1/superset/guest-token",
        json={"dashboard_id": exec_dashboard_id},
        cookies={
            settings.SESSION_COOKIE_NAME: session_cookie,
            settings.CSRF_COOKIE_NAME: csrf_cookie,
        },
        headers={settings.CSRF_HEADER_NAME: csrf_cookie},
    )
    assert res.status_code == 403
    assert res.json()["error_code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_guest_token_issued_for_permitted_dashboard(client: AsyncClient, seed_data):
    """Authorized user successfully receives signed Superset guest token."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@bank.internal", "password": "ManagerPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = login_res.cookies[settings.CSRF_COOKIE_NAME]

    branch_dashboard_id = seed_data["dash_branch"].id

    mock_token_response = SupersetGuestTokenResponse(
        token="mocked.signed.guest.jwt.token",
        superset_dashboard_id="uuid-branch-1",
        superset_domain="http://localhost:8088",
        expires_in=300,
        dashboard_title="Branch Metrics",
        requires_branch_scope=True,
    )

    with patch(
        "app.services.superset_service.SupersetService.generate_guest_token",
        new=AsyncMock(return_value=mock_token_response),
    ):
        res = await client.post(
            "/api/v1/superset/guest-token",
            json={"dashboard_id": branch_dashboard_id},
            cookies={
                settings.SESSION_COOKIE_NAME: session_cookie,
                settings.CSRF_COOKIE_NAME: csrf_cookie,
            },
            headers={settings.CSRF_HEADER_NAME: csrf_cookie},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["token"] == "mocked.signed.guest.jwt.token"
        assert data["superset_dashboard_id"] == "uuid-branch-1"
        assert data["superset_domain"] == "http://localhost:8088"
        assert data["requires_branch_scope"] is True


@pytest.mark.asyncio
async def test_superset_status_check(client: AsyncClient, seed_data):
    """Superset status endpoint reports configuration status."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "AdminPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]

    res = await client.get(
        "/api/v1/superset/status",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie},
    )
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    assert "connected" in data
    assert "superset_url" in data


# ---------------------------------------------------------------------------
# Unit tests for SupersetService.generate_guest_token CSRF flow
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int, json_body: dict) -> MagicMock:
    """Build a synchronous mock that behaves like an httpx.Response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = json_body
    if status_code >= 400:
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock,
        )
    else:
        mock.raise_for_status.return_value = None
    mock.text = str(json_body)
    return mock


def _configured_service() -> SupersetService:
    """Return a SupersetService that reports as configured."""
    svc = SupersetService(
        base_url="http://superset.test:8088",
        admin_username="svc_admin",
        admin_password="Str0ngS3rviceP@ss!",
    )
    return svc


def _mock_user() -> MagicMock:
    user = MagicMock()
    user.email = "analyst@bank.internal"
    user.full_name = "Ana Lyst"
    user.assigned_branch_id = None
    return user


def _mock_dashboard(requires_branch_scope: bool = False) -> MagicMock:
    dash = MagicMock()
    dash.superset_dashboard_id = "uuid-dash-0001"
    dash.title = "Test Dashboard"
    dash.requires_branch_scope = requires_branch_scope
    return dash


@pytest.mark.asyncio
async def test_generate_guest_token_csrf_flow_success():
    """CSRF token is fetched first; guest-token POST includes X-CSRFToken header."""
    svc = _configured_service()
    # Patch get_admin_token so no real HTTP call is made
    svc.get_admin_token = AsyncMock(return_value="valid-admin-token")

    csrf_response = _make_mock_response(200, {"result": "csrf-abc123"})
    guest_response = _make_mock_response(200, {"token": "guest.jwt.token"})

    # Track calls in order
    call_log: list[str] = []

    async def fake_get(url, **kwargs):
        call_log.append(f"GET {url}")
        assert "Bearer valid-admin-token" in kwargs.get("headers", {}).get("Authorization", "")
        return csrf_response

    async def fake_post(url, **kwargs):
        call_log.append(f"POST {url}")
        sent_headers = kwargs.get("headers", {})
        # Both Bearer and CSRF header must be present
        assert "Bearer valid-admin-token" in sent_headers.get("Authorization", "")
        assert sent_headers.get("X-CSRFToken") == "csrf-abc123"
        return guest_response

    mock_client = MagicMock()
    mock_client.get = fake_get
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.superset_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.generate_guest_token(_mock_user(), _mock_dashboard())

    assert result.token == "guest.jwt.token"
    assert result.superset_dashboard_id == "uuid-dash-0001"
    assert result.superset_domain == "http://superset.test:8088"
    assert "GET" in call_log[0] and "csrf_token" in call_log[0]
    assert "POST" in call_log[1] and "guest_token" in call_log[1]


@pytest.mark.asyncio
async def test_generate_guest_token_csrf_fetch_http_error():
    """SupersetIntegrationError is raised when the CSRF endpoint returns an error status."""
    svc = _configured_service()
    svc.get_admin_token = AsyncMock(return_value="valid-admin-token")

    csrf_error_response = _make_mock_response(500, {"message": "Internal Server Error"})

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=csrf_error_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.superset_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(SupersetIntegrationError, match="CSRF token"):
            await svc.generate_guest_token(_mock_user(), _mock_dashboard())


@pytest.mark.asyncio
async def test_generate_guest_token_csrf_missing_result_key():
    """SupersetIntegrationError is raised when the CSRF response has no 'result' key."""
    svc = _configured_service()
    svc.get_admin_token = AsyncMock(return_value="valid-admin-token")

    # 200 OK but body has no 'result'
    csrf_response = _make_mock_response(200, {"unexpected_key": "no-token-here"})

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=csrf_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.superset_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(SupersetIntegrationError, match="'result'"):
            await svc.generate_guest_token(_mock_user(), _mock_dashboard())


@pytest.mark.asyncio
async def test_generate_guest_token_refreshes_admin_and_csrf_on_401():
    """On a 401 from the guest-token endpoint, admin token AND CSRF token are both refreshed."""
    svc = _configured_service()

    # First call returns initial token; second call (force_refresh) returns refreshed token
    svc.get_admin_token = AsyncMock(
        side_effect=["initial-admin-token", "refreshed-admin-token"]
    )

    csrf_initial = _make_mock_response(200, {"result": "csrf-initial"})
    csrf_refreshed = _make_mock_response(200, {"result": "csrf-refreshed"})
    guest_401 = _make_mock_response(401, {"message": "Token expired"})
    guest_ok = _make_mock_response(200, {"token": "new.guest.jwt"})

    get_calls: list[str] = []
    post_calls: list[dict] = []

    async def fake_get(url, **kwargs):
        get_calls.append(url)
        return csrf_initial if len(get_calls) == 1 else csrf_refreshed

    async def fake_post(url, **kwargs):
        headers = kwargs.get("headers", {})
        post_calls.append({"X-CSRFToken": headers.get("X-CSRFToken"), "Auth": headers.get("Authorization")})
        return guest_401 if len(post_calls) == 1 else guest_ok

    mock_client = MagicMock()
    mock_client.get = fake_get
    mock_client.post = fake_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.superset_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.generate_guest_token(_mock_user(), _mock_dashboard())

    assert result.token == "new.guest.jwt"
    # get_admin_token was called twice: initial + force_refresh
    assert svc.get_admin_token.call_count == 2
    assert svc.get_admin_token.call_args_list[1][1].get("force_refresh") is True
    # Two CSRF fetches and two POST attempts
    assert len(get_calls) == 2
    assert len(post_calls) == 2
    # Retry used the refreshed CSRF and admin tokens
    assert post_calls[1]["X-CSRFToken"] == "csrf-refreshed"
    assert "refreshed-admin-token" in post_calls[1]["Auth"]
