import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seed_data):
    """Test successful login sets HTTP-only session cookie and returns user profile."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@bank.internal"
    assert data["is_superuser"] is True
    assert len(data["roles"]) == 1

    # Check cookies
    cookies = response.cookies
    assert settings.SESSION_COOKIE_NAME in cookies
    assert settings.CSRF_COOKIE_NAME in cookies


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, seed_data):
    """Test login failure with invalid password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient, seed_data):
    """Test login failure with unknown email."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@bank.internal", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_auth_me_with_cookie(client: AsyncClient, seed_data):
    """Test accessing /me endpoint with HTTP-only session cookie."""
    # 1. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@bank.internal", "password": "ManagerPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]

    # 2. Get /me using cookie
    me_res = await client.get(
        "/api/v1/auth/me",
        cookies={settings.SESSION_COOKIE_NAME: session_cookie},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "manager@bank.internal"
    assert me_data["roles"][0]["name"] == "branch_manager"
    assert me_data["assigned_branch_id"] == "BR-101"


@pytest.mark.asyncio
async def test_auth_me_unauthorized(client: AsyncClient, seed_data):
    """Test /me returns 401 without cookie."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_csrf_token_endpoint(client: AsyncClient):
    """Test /csrf endpoint provides fresh token."""
    response = await client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    data = response.json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 20
    assert settings.CSRF_COOKIE_NAME in response.cookies
