import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_admin_sees_all_dashboards(client: AsyncClient, seed_data):
    """Superuser/admin should see all active dashboards."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "AdminPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]

    res = await client.get(
        "/api/v1/dashboards/",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie},
    )
    assert res.status_code == 200
    slugs = [d["slug"] for d in res.json()]
    assert "exec-overview" in slugs
    assert "branch-metrics" in slugs
    assert "analyst-risk" in slugs


@pytest.mark.asyncio
async def test_role_scoped_dashboards(client: AsyncClient, seed_data):
    """Manager should only see dashboards permitted for branch_manager."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@bank.internal", "password": "ManagerPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]

    res = await client.get(
        "/api/v1/dashboards/",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie},
    )
    assert res.status_code == 200
    slugs = [d["slug"] for d in res.json()]
    assert "branch-metrics" in slugs
    assert "exec-overview" not in slugs
    assert "analyst-risk" not in slugs


@pytest.mark.asyncio
async def test_unauthorized_dashboard_detail_access(client: AsyncClient, seed_data):
    """Attempting to access a dashboard not in user's role must return 403."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@bank.internal", "password": "ManagerPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]

    exec_dashboard_id = seed_data["dash_exec"].id
    res = await client.get(
        f"/api/v1/dashboards/{exec_dashboard_id}",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie},
    )
    assert res.status_code == 403
    assert res.json()["error_code"] == "PERMISSION_DENIED"
