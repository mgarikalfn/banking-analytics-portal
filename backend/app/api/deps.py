from typing import AsyncGenerator, Callable, List, Optional
from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationError,
    CSRFValidationError,
    PermissionDeniedError,
)
from app.core.security import decode_jwt_token, verify_csrf_token
from app.models.user import User
from app.repositories.user_repo import UserRepository


async def get_current_user_optional(
    request: Request,
    portal_session: Optional[str] = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract and validate the user from HTTP-only session cookie or Bearer header."""
    token = portal_session

    # Support Bearer token header fallback (useful for automated testing and tools)
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    if not token:
        return None

    payload = decode_jwt_token(token)
    if not payload or payload.get("type") != "access":
        return None

    try:
        user_id = int(payload.get("sub", 0))
    except (ValueError, TypeError):
        return None

    user_repo = UserRepository(db)
    user = await user_repo.get_with_roles(user_id)
    if not user or not user.is_active:
        return None

    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Dependency that requires an authenticated, active user."""
    if not user:
        raise AuthenticationError("Authentication required. Session is invalid or expired.")
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires superuser privileges."""
    if not current_user.is_superuser:
        raise PermissionDeniedError("Administrator privileges required.")
    return current_user


def require_roles(allowed_roles: List[str]) -> Callable:
    """Dependency factory enforcing Role-Based Access Control (RBAC)."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        user_role_names = {r.name.lower() for r in current_user.roles}
        required_names = {r.lower() for r in allowed_roles}

        if not (user_role_names & required_names):
            raise PermissionDeniedError(
                f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker


async def verify_csrf(
    request: Request,
    csrf_cookie: Optional[str] = Cookie(None, alias=settings.CSRF_COOKIE_NAME),
    csrf_header: Optional[str] = Header(None, alias=settings.CSRF_HEADER_NAME),
) -> None:
    """Validate CSRF token for state-changing requests (Double-Submit Cookie pattern)."""
    # Safe HTTP methods do not require CSRF
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # In local testing or API calls using Bearer authorization without cookies, CSRF can be bypassed
    has_bearer = bool(request.headers.get("authorization", "").startswith("Bearer "))
    has_cookie = bool(request.cookies.get(settings.SESSION_COOKIE_NAME))

    if has_bearer and not has_cookie:
        return

    if not verify_csrf_token(csrf_cookie, csrf_header):
        raise CSRFValidationError(
            "CSRF verification failed: Mismatched or missing CSRF token in request header."
        )
