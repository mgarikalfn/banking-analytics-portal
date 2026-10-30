from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, verify_csrf
from app.core.config import settings
from app.core.security import generate_csrf_token
from app.models.user import User
from app.schemas.token import CSRFResponse, LoginRequest
from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/csrf", response_model=CSRFResponse)
async def get_csrf_token(response: Response) -> CSRFResponse:
    """Generate and set a fresh CSRF token in a readable cookie and response body."""
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,  # Must be readable by client JS to send in X-CSRF-Token header
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        max_age=3600 * 24,
    )
    return CSRFResponse(csrf_token=csrf_token)


@router.post("/login", response_model=UserRead)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Authenticate user with email and password, setting secure HTTP-only session cookie."""
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    user = await auth_service.authenticate(login_data.email, login_data.password)
    access_token, _ = auth_service.generate_tokens(user)

    # Secure HTTP-only session cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,  # Prevent JavaScript XSS access
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    # Also issue fresh CSRF token for subsequent state mutations
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN or None,
        max_age=3600 * 24,
    )

    client_ip = request.client.host if request.client else "unknown"
    await audit_service.log(
        user_id=user.id,
        action="LOGIN_SUCCESS",
        resource="auth",
        details=f"User {user.email} logged in successfully",
        ip_address=client_ip,
    )

    return UserRead.model_validate(user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(verify_csrf),
) -> dict:
    """Clear session cookie and log logout."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        domain=settings.COOKIE_DOMAIN or None,
    )
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        domain=settings.COOKIE_DOMAIN or None,
    )

    audit_service = AuditService(db)
    client_ip = request.client.host if request.client else "unknown"
    await audit_service.log(
        user_id=current_user.id,
        action="LOGOUT",
        resource="auth",
        details=f"User {current_user.email} logged out",
        ip_address=client_ip,
    )

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Retrieve profile and permissions for currently authenticated user."""
    return UserRead.model_validate(current_user)
