from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.schemas.superset import SupersetGuestTokenResponse


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
