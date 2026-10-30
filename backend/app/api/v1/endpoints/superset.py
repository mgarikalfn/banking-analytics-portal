from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, verify_csrf
from app.models.user import User
from app.schemas.superset import (
    SupersetGuestTokenRequest,
    SupersetGuestTokenResponse,
    SupersetHealthResponse,
)
from app.services.audit_service import AuditService
from app.services.dashboard_service import DashboardService
from app.services.superset_service import SupersetService

router = APIRouter()


@router.post(
    "/guest-token",
    response_model=SupersetGuestTokenResponse,
    dependencies=[Depends(verify_csrf)],
)
async def generate_guest_token(
    payload: SupersetGuestTokenRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupersetGuestTokenResponse:
    """Validate user authorization and generate an Apache Superset guest token.
    
    1. Validates that current user has active permission to access the requested dashboard.
    2. Securely requests guest token from Superset REST API using backend service credentials.
    3. Records an audit log of the dashboard access.
    """
    dashboard_service = DashboardService(db)
    audit_service = AuditService(db)
    superset_service = SupersetService()

    # Crucial security step: verify user access before issuing any token
    dashboard = await dashboard_service.check_access(
        user_id=current_user.id,
        dashboard_id=payload.dashboard_id,
        is_superuser=current_user.is_superuser,
    )

    # Request guest token from Superset
    token_response = await superset_service.generate_guest_token(
        user=current_user, dashboard=dashboard
    )

    # Audit log entry
    client_ip = request.client.host if request.client else "unknown"
    await audit_service.log(
        user_id=current_user.id,
        action="VIEW_DASHBOARD",
        resource=f"dashboard:{dashboard.id}",
        details=f"Generated Superset guest token for dashboard '{dashboard.title}' (slug: {dashboard.slug})",
        ip_address=client_ip,
    )

    return token_response


@router.get("/status", response_model=SupersetHealthResponse)
async def get_superset_status(
    _: User = Depends(get_current_user),
) -> SupersetHealthResponse:
    """Check connectivity and configuration status of Apache Superset integration."""
    superset_service = SupersetService()
    health = await superset_service.check_health()
    return SupersetHealthResponse(
        configured=health["configured"],
        superset_url=health["superset_url"],
        connected=health["connected"],
        status_detail=health["status_detail"],
    )
