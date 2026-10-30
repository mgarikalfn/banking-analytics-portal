import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_csrf_validation_blocks_request_without_header(client: AsyncClient, seed_data):
    """State-changing request with cookie but missing CSRF header must be blocked with 403."""
    # 1. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "AdminPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = login_res.cookies[settings.CSRF_COOKIE_NAME]

    # 2. Attempt POST logout without X-CSRF-Token header
    response = await client.post(
        "/api/v1/auth/logout",
        cookies={
            settings.SESSION_COOKIE_NAME: session_cookie,
            settings.CSRF_COOKIE_NAME: csrf_cookie,
        },
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "CSRF_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_csrf_validation_blocks_mismatched_tokens(client: AsyncClient, seed_data):
    """State-changing request with mismatched CSRF header vs cookie must be blocked."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "AdminPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = login_res.cookies[settings.CSRF_COOKIE_NAME]

    response = await client.post(
        "/api/v1/auth/logout",
        cookies={
            settings.SESSION_COOKIE_NAME: session_cookie,
            settings.CSRF_COOKIE_NAME: csrf_cookie,
        },
        headers={settings.CSRF_HEADER_NAME: "forged-csrf-token-12345"},
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "CSRF_VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_csrf_validation_allows_valid_token(client: AsyncClient, seed_data):
    """State-changing request with matching CSRF cookie and header succeeds."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@bank.internal", "password": "AdminPass123!"},
    )
    session_cookie = login_res.cookies[settings.SESSION_COOKIE_NAME]
    csrf_cookie = login_res.cookies[settings.CSRF_COOKIE_NAME]

    response = await client.post(
        "/api/v1/auth/logout",
        cookies={
            settings.SESSION_COOKIE_NAME: session_cookie,
            settings.CSRF_COOKIE_NAME: csrf_cookie,
        },
        headers={settings.CSRF_HEADER_NAME: csrf_cookie},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"
