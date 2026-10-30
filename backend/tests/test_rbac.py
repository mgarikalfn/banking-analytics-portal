import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_admin_endpoints_blocked_for_non_admin(client: AsyncClient, seed_data):
    """Endpoints restricted to superuser must return 403 for non-superuser."""
    # Manager login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@bank.internal", "password": "ManagerPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = login_res.cookies[settings.CSRF_COOKIE_NAME]

    # Attempt to list users (admin only)
    users_res = await client.get(
        "/api/v1/users/",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie},
    )
    assert users_res.status_code == 403
    assert users_res.json()["error_code"] == "PERMISSION_DENIED"

    # Attempt to create dashboard (admin only)
    create_res = await client.post(
        "/api/v1/dashboards/",
        json={
            "slug": "unauthorized-dash",
            "title": "Unauthorized Dash",
            "superset_dashboard_id": "test-id",
        },
        cookies={
            settings.SESSION_COOKIE_NAME: session_cookie,
            settings.CSRF_COOKIE_NAME: csrf_cookie,
        },
        headers={settings.CSRF_HEADER_NAME: csrf_cookie},
    )
    assert create_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_manage_users(client: AsyncClient, seed_data):
    """Admin can list and create users."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "AdminPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = login_res.cookies[settings.CSRF_COOKIE_NAME]

    # List users
    users_res = await client.get(
        "/api/v1/users/",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie},
    )
    assert users_res.status_code == 200
    assert len(users_res.json()) >= 3

    # Create user
    create_res = await client.post(
        "/api/v1/users/",
        json={
            "email": "newofficer@bank.internal",
            "password": "SecurePassword123!",
            "full_name": "Compliance Officer New",
            "is_active": True,
            "is_superuser": False,
        },
        cookies={
            settings.SESSION_COOKIE_NAME: session_cookie,
            settings.CSRF_COOKIE_NAME: csrf_cookie,
        },
        headers={settings.CSRF_HEADER_NAME: csrf_cookie},
    )
    assert create_res.status_code == 201
    assert create_res.json()["email"] == "newofficer@bank.internal"
